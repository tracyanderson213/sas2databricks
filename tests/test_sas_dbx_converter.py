"""
Test suite for sas_dbx.py's SAS-to-Databricks translation functions.

Two kinds of tests here, and they're intentionally kept separate:

  REGRESSION tests  -- exercise patterns the converter already handles
                        correctly. These should always pass. If one of
                        these starts failing, something that used to work
                        broke.

  GAP tests (xfail) -- exercise the 10 edge cases identified in code
                        review that the converter does not yet handle
                        correctly. Each is marked `xfail(strict=False)`:
                        they show up as "expected failure" today, which
                        is not a build-breaking failure. When you fix the
                        underlying gap, the test flips to XPASS -- a
                        clear, visible signal that you closed that gap
                        (and a prompt to remove the xfail marker).

Run:  pytest -v
Run only the gap/backlog tests:      pytest -v -m gap
Run only the regression tests:       pytest -v -m "not gap"
"""
import pytest

pytestmark = pytest.mark.usefixtures("sas_dbx_module")


def gap(reason):
    """Shorthand for marking a known-limitation test."""
    return pytest.mark.xfail(reason=reason, strict=False)


# ==============================================================================
# REGRESSION TESTS -- patterns the converter already handles correctly
# ==============================================================================

class TestMergeRegression:
    def test_simple_left_join_detected(self, sas_dbx_module):
        sas = """
        data work.claims_elig;
            merge work.claims_in (in=inclaim) work.members (in=inmember);
            by member_id;
            if inclaim;
        run;
        """
        result = sas_dbx_module.translate_merge_to_join(sas, "")
        assert len(result) == 1
        assert result[0]["join_type"] == "left"
        assert result[0]["by_vars"] == "member_id"
        assert len(result[0]["tables"]) == 2

    def test_three_table_merge_parses_all_tables(self, sas_dbx_module):
        """Table parsing itself isn't limited to two tables -- this should
        already work. (Join-type inference for 3+ tables is a separate,
        known gap -- see TestMergeGaps below.)"""
        sas = """
        data work.claims_multi_merge;
            merge work.claims (in=inclaim) work.members (in=inmember) work.providers (in=inprov);
            by member_id;
            if inclaim or inmember;
        run;
        """
        result = sas_dbx_module.translate_merge_to_join(sas, "")
        assert len(result) == 1
        assert len(result[0]["tables"]) == 3
        assert result[0]["tables"][2]["in_flag"] == "inprov"


class TestRetainRegression:
    def test_simple_running_total_detected(self, sas_dbx_module):
        sas = """
        data work.claims_running;
            set work.claims_benefit;
            by member_id;
            retain ytd_paid 0;
            if first.member_id then ytd_paid = 0;
            ytd_paid + billed_amount;
        run;
        """
        result = sas_dbx_module.translate_retain_to_window(sas)
        assert len(result) == 1
        assert result[0]["retain_var"] == "ytd_paid"
        assert result[0]["accum_source"] == "billed_amount"
        assert result[0]["partition_by"] == "member_id"


class TestDatalinesRegression:
    def test_basic_numeric_and_string_columns_parsed(self, sas_dbx_module):
        sas = """
        data work.members;
            length member_id $10 plan_id $6;
            input member_id $ plan_id $ balance;
            datalines;
        M0001 PLNA01 120.50
        M0002 PLNB02 0
        ;
        run;
        """
        result = sas_dbx_module.parse_sas_datalines(sas)
        assert "work_members" in result
        info = result["work_members"]
        assert info["columns"] == ["member_id", "plan_id", "balance"]
        assert info["row_count"] == 2


class TestProcFormatRegression:
    def test_basic_quoted_mapping_extracted(self, sas_dbx_module):
        sas = """
        proc format;
            value $diagcat
                'E11' = 'DIABETES'
                'I10' = 'HYPERTENSION'
                other = 'OTHER';
        run;
        """
        result = sas_dbx_module.extract_proc_formats(sas)
        assert "diagcat" in result
        assert result["diagcat"]["mappings"] == {
            "E11": "DIABETES",
            "I10": "HYPERTENSION",
        }
        assert result["diagcat"]["default"] == "OTHER"


class TestMedallionLayerRegression:
    @pytest.mark.parametrize(
        "table_name,expected_layer",
        [
            ("bronze_claims", "bronze"),
            ("raw_claims", "bronze"),
            ("gold_summary", "gold"),
            ("final_report", "gold"),
            ("clm_adjudicated", "gold"),
            ("work_claims_elig", "silver"),
            ("work_claims_in", "bronze"),
            ("members", "bronze"),
        ],
    )
    def test_priority_rules(self, sas_dbx_module, table_name, expected_layer):
        assert sas_dbx_module.detect_medallion_layer(table_name, "", "") == expected_layer


class TestShouldBeViewRegression:
    @pytest.mark.parametrize(
        "table_name,expected_is_view",
        [
            ("bronze_claims", False),
            ("gold_summary", False),
            ("work_claims_elig", True),
            ("sort_raw", True),
        ],
    )
    def test_view_vs_table_rules(self, sas_dbx_module, table_name, expected_is_view):
        assert sas_dbx_module.detect_should_be_view(table_name, "", "") == expected_is_view


class TestRobustness:
    def test_macro_wrapped_data_step_does_not_crash_translators(self, sas_dbx_module):
        """Whatever the converter's macro-handling story ends up being,
        feeding it macro-wrapped code should never raise -- it should
        degrade to 'nothing recognized here' rather than throwing."""
        sas = """
        %macro adjudicate(dsin=, dsout=);
            data &dsout;
                set &dsin;
                if elig_flag = 'N' then adj_status = 'DENIED';
                else adj_status = 'APPROVED';
            run;
        %mend;
        %adjudicate(dsin=work.claims_elig, dsout=work.claims_final);
        """
        # Should not raise:
        merge_result = sas_dbx_module.translate_merge_to_join(sas, "")
        retain_result = sas_dbx_module.translate_retain_to_window(sas)
        assert isinstance(merge_result, list)
        assert isinstance(retain_result, list)


# ==============================================================================
# GAP TESTS -- known limitations from code review, marked xfail(strict=False)
# ==============================================================================

class TestRetainGaps:
    @gap(
        "translate_retain_to_window only captures the first variable named "
        "after RETAIN (retain\\s+(\\w+)). A statement declaring multiple "
        "retained variables (`retain ytd_paid ytd_count 0 0;`) is only "
        "partially detected."
    )
    @pytest.mark.gap
    def test_retain_multiple_variables_all_detected(self, sas_dbx_module):
        sas = """
        data work.claims_multi;
            set work.claims_benefit;
            by member_id;
            retain ytd_paid ytd_count 0 0;
            if first.member_id then do;
                ytd_paid = 0;
                ytd_count = 0;
            end;
            ytd_paid + billed_amount;
            ytd_count + 1;
        run;
        """
        result = sas_dbx_module.translate_retain_to_window(sas)
        detected_vars = {r["retain_var"] for r in result}
        assert detected_vars == {"ytd_paid", "ytd_count"}

    @gap(
        "translate_retain_to_window only recognizes the running-sum idiom "
        "(`var + accum_source;`). RETAIN used for carry-forward-last-"
        "non-missing-value (no arithmetic at all) is not detected."
    )
    @pytest.mark.gap
    def test_retain_carry_forward_pattern_detected(self, sas_dbx_module):
        sas = """
        data work.claims_carry;
            set work.claims_sorted;
            by member_id;
            retain last_diag_code;
            if not missing(diag_code) then last_diag_code = diag_code;
        run;
        """
        result = sas_dbx_module.translate_retain_to_window(sas)
        assert len(result) >= 1
        assert result[0]["retain_var"] == "last_diag_code"


class TestMergeGaps:
    @gap(
        "translate_merge_to_join's join-type inference only inspects "
        "tables[0] and tables[1]. A third (or later) table's in= flag is "
        "parsed into `tables` but never consulted when deciding join type "
        "or building the where_clause."
    )
    @pytest.mark.gap
    def test_third_table_flag_reflected_in_join_logic(self, sas_dbx_module):
        sas = """
        data work.claims_multi_merge;
            merge work.claims (in=inclaim) work.members (in=inmember) work.providers (in=inprov);
            by member_id;
            if inclaim or inmember;
        run;
        """
        result = sas_dbx_module.translate_merge_to_join(sas, "")
        pattern = result[0]
        # The third table's flag should show up somewhere in the join
        # logic once multi-table merges are handled -- today it's parsed
        # into `tables` but has no effect on join_type/where_clause.
        assert pattern.get("join_type") == "multi" or "inprov" in str(
            pattern.get("where_clause")
        )

    @gap(
        "translate_merge_to_join grabs only the FIRST `if` statement after "
        "the merge (re.search, not aware of statement order or intent). "
        "If an assignment IF happens to appear before the filter IF, the "
        "filter is missed and join_type falls back to the 'full' default."
    )
    @pytest.mark.gap
    def test_filter_if_detected_even_when_not_first_statement(self, sas_dbx_module):
        sas = """
        data work.claims_reordered;
            merge work.claims_in (in=inclaim) work.members (in=inmember);
            by member_id;
            if inmember = 0 then elig_flag = 'N';
            if inclaim;
        run;
        """
        result = sas_dbx_module.translate_merge_to_join(sas, "")
        assert result[0]["join_type"] == "left"


class TestLibnameNormalizationGaps:
    @gap(
        "post_process_converted_code's table-reference normalization "
        "(Pattern D) hardcodes the library list to (work|clm|lib). Any "
        "other LIBNAME -- edw, stg, elig, and other client-specific names "
        "common in real SAS estates -- passes through unqualified."
    )
    @pytest.mark.gap
    def test_custom_libname_normalized(self, sas_dbx_module):
        code = (
            'def foo():\n'
            '    return spark.sql("""SELECT * FROM edw.claims_raw""")\n'
        )
        result = sas_dbx_module.post_process_converted_code(
            code,
            table_analysis=[],
            sas_source_text="",
            api_style="dp",
            schema_bronze="bronze",
            schema_silver="silver",
            schema_gold="gold",
        )
        assert "FROM edw_claims_raw" in result


class TestDatalinesGaps:
    @gap(
        "parse_sas_datalines splits each data row on whitespace "
        "(line.split()) with no support for quoted/multi-word string "
        "values or SAS missing-value markers ('.'). A row whose column "
        "count doesn't match after a naive split is silently dropped."
    )
    @pytest.mark.gap
    def test_embedded_space_and_missing_value_handled(self, sas_dbx_module):
        sas = """
        data work.members_named;
            length member_id $10 member_name $20;
            input member_id $ member_name $ balance;
            datalines;
        M0001 John Smith 120.50
        M0002 . 0
        ;
        run;
        """
        result = sas_dbx_module.parse_sas_datalines(sas)
        info = result.get("work_members_named", {})
        assert info.get("row_count") == 2
        first_row = info.get("data", [[]])[0]
        # member_name should be the single value "John Smith", not split
        # across two positions.
        assert "John Smith" in first_row or "John_Smith" in first_row


class TestProcFormatGaps:
    @gap(
        "extract_proc_formats' pair_pattern requires quotes around both "
        "the key and the value. SAS numeric-range formats (`low-17 = "
        "'MINOR'`, `18-64 = 'ADULT'`) use unquoted numeric range keys and "
        "are not extracted at all -- only the `other=` default is caught."
    )
    @pytest.mark.gap
    def test_numeric_range_format_extracted(self, sas_dbx_module):
        sas = """
        proc format;
            value agebucket
                low-17  = 'MINOR'
                18-64   = 'ADULT'
                65-high = 'SENIOR'
                other   = 'UNKNOWN';
        run;
        """
        result = sas_dbx_module.extract_proc_formats(sas)
        assert len(result.get("agebucket", {}).get("mappings", {})) == 3


class TestFirstLastGaps:
    @gap(
        "FIRST./LAST. duplicate-detection (pattern guide Section 5) has "
        "no dedicated translator in this file at all -- it's referenced "
        "only as a trigger phrase inside the RETAIN regex, never as its "
        "own ROW_NUMBER()/COUNT()-OVER generator for the standalone "
        "duplicate-flagging idiom."
    )
    @pytest.mark.gap
    def test_first_last_translator_exists(self, sas_dbx_module):
        candidate_names = [
            "translate_first_last_to_window",
            "translate_first_last",
            "detect_duplicate_flag_pattern",
        ]
        assert any(hasattr(sas_dbx_module, name) for name in candidate_names)


class TestNestedIfGaps:
    @gap(
        "Nested IF/THEN/ELSE consolidation into a single CASE WHEN "
        "(pattern guide Section 6) is not implemented -- the converter "
        "relies entirely on sas2databricks' native output for branching "
        "logic, which is the source of the original 'multiple columns "
        "with the same name' bug."
    )
    @pytest.mark.gap
    def test_case_when_consolidation_function_exists(self, sas_dbx_module):
        candidate_names = [
            "consolidate_branches_to_case_when",
            "translate_nested_if_to_case",
        ]
        assert any(hasattr(sas_dbx_module, name) for name in candidate_names)


class TestMacroDetectionGaps:
    @gap(
        "No macro detection exists anywhere in this file (no %macro, "
        "%let, %do, or symput handling). Macro-wrapped DATA steps pass "
        "straight through the pipeline with no flag for manual review, "
        "unlike SMF's explicit review_required posture for the same case."
    )
    @pytest.mark.gap
    def test_macro_wrapped_code_is_flagged_for_review(self, sas_dbx_module):
        sas = """
        %macro adjudicate(dsin=, dsout=);
            data &dsout;
                set &dsin;
                if elig_flag = 'N' then adj_status = 'DENIED';
                else adj_status = 'APPROVED';
            run;
        %mend;
        %adjudicate(dsin=work.claims_elig, dsout=work.claims_final);
        """
        candidate_names = ["detect_sas_macros", "flag_macro_dependent_code"]
        has_detector = any(hasattr(sas_dbx_module, name) for name in candidate_names)
        assert has_detector
