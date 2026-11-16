import os
import tempfile
import zipfile
import xml.etree.ElementTree as ET


# =========================================================
# NAMESPACES
# =========================================================

MANIFEST_NS = {
    "cc": (
        "http://www.imsglobal.org/"
        "xsd/imsccv1p1/imscp_v1p1"
    )
}

QTI_NS = {
    "qti": (
        "http://www.imsglobal.org/"
        "xsd/ims_qtiasiv1p2"
    )
}

CANVAS_NS = {
    "canvas": (
        "http://canvas.instructure.com/"
        "xsd/cccv1p0"
    )
}


# =========================================================
# HELPERS
# =========================================================

def metadata_value(item, field_name):
    """
    Read a Canvas QTI metadata field from an item.
    """

    fields = item.findall(
        ".//qti:qtimetadatafield",
        QTI_NS,
    )

    for field in fields:

        label = field.find(
            "qti:fieldlabel",
            QTI_NS,
        )

        entry = field.find(
            "qti:fieldentry",
            QTI_NS,
        )

        if (
            label is not None
            and label.text == field_name
        ):
            if entry is None:
                return None

            return entry.text

    return None


def numeric_text(element):
    if element is None:
        return None

    if element.text is None:
        return None

    try:
        return float(
            element.text.strip()
        )
    except ValueError:
        return None


# =========================================================
# MAIN VALIDATOR
# =========================================================

def validate_qti_package(
    zip_path,
    expected_questions=None,
):
    """
    Validate CourseCraft's Canvas New Quiz package.

    This validates:

    - ZIP integrity
    - IMS Common Cartridge manifest
    - Canvas assessment metadata
    - assessment XML
    - question metadata
    - choice cardinality
    - numeric response structure
    - numeric tolerance/range
    - manifest dependencies
    - package paths

    Passing this validator does not guarantee that
    Canvas will import the package, but it catches
    the major structural problems locally.
    """

    results = []
    errors = []
    warnings = []

    # =====================================================
    # ZIP
    # =====================================================

    if not os.path.exists(zip_path):
        errors.append(
            f"Package does not exist: {zip_path}"
        )

        return results, errors, warnings

    if not zipfile.is_zipfile(zip_path):
        errors.append(
            "File is not a valid ZIP archive."
        )

        return results, errors, warnings

    results.append(
        "Valid ZIP archive"
    )

    with zipfile.ZipFile(
        zip_path,
        "r",
    ) as package:

        bad_file = package.testzip()

        if bad_file is not None:
            errors.append(
                f"Corrupt ZIP entry: {bad_file}"
            )

            return results, errors, warnings

        results.append(
            "ZIP integrity passed"
        )

        names = package.namelist()

        # =================================================
        # REQUIRED PACKAGE CONTENT
        # =================================================

        if "imsmanifest.xml" not in names:
            errors.append(
                "imsmanifest.xml is missing."
            )

            return results, errors, warnings

        results.append(
            "imsmanifest.xml found"
        )

        if (
            "non_cc_assessments/"
            not in names
        ):
            warnings.append(
                "non_cc_assessments/ folder "
                "is not present."
            )
        else:
            results.append(
                "non_cc_assessments/ found"
            )

        assessment_files = [
            name
            for name in names
            if name.endswith(".xml")
            and name != "imsmanifest.xml"
            and not name.endswith(
                "assessment_meta.xml"
            )
        ]

        meta_files = [
            name
            for name in names
            if name.endswith(
                "assessment_meta.xml"
            )
        ]

        if len(assessment_files) != 1:
            errors.append(
                "Expected exactly one assessment XML "
                f"but found {len(assessment_files)}."
            )

            return results, errors, warnings

        if len(meta_files) != 1:
            errors.append(
                "Expected exactly one assessment_meta.xml "
                f"but found {len(meta_files)}."
            )

            return results, errors, warnings

        assessment_relative = (
            assessment_files[0]
        )

        meta_relative = meta_files[0]

        results.append(
            "One assessment XML found"
        )

        results.append(
            "assessment_meta.xml found"
        )

        # =================================================
        # EXTRACT
        # =================================================

        with tempfile.TemporaryDirectory() as temp_dir:

            package.extractall(
                temp_dir
            )

            manifest_path = os.path.join(
                temp_dir,
                "imsmanifest.xml",
            )

            assessment_path = os.path.join(
                temp_dir,
                assessment_relative,
            )

            meta_path = os.path.join(
                temp_dir,
                meta_relative,
            )

            # =============================================
            # XML PARSING
            # =============================================

            try:
                manifest_tree = ET.parse(
                    manifest_path
                )

                manifest_root = (
                    manifest_tree.getroot()
                )

                results.append(
                    "Manifest XML is well formed"
                )

            except ET.ParseError as error:

                errors.append(
                    f"Manifest XML error: {error}"
                )

                return (
                    results,
                    errors,
                    warnings,
                )

            try:
                assessment_tree = ET.parse(
                    assessment_path
                )

                assessment_root = (
                    assessment_tree.getroot()
                )

                results.append(
                    "Assessment XML is well formed"
                )

            except ET.ParseError as error:

                errors.append(
                    f"Assessment XML error: {error}"
                )

                return (
                    results,
                    errors,
                    warnings,
                )

            try:
                meta_tree = ET.parse(
                    meta_path
                )

                meta_root = (
                    meta_tree.getroot()
                )

                results.append(
                    "assessment_meta.xml "
                    "is well formed"
                )

            except ET.ParseError as error:

                errors.append(
                    "assessment_meta.xml error: "
                    f"{error}"
                )

                return (
                    results,
                    errors,
                    warnings,
                )

            # =============================================
            # MANIFEST NAMESPACE
            # =============================================

            expected_manifest_tag = (
                "{"
                + MANIFEST_NS["cc"]
                + "}manifest"
            )

            if (
                manifest_root.tag
                != expected_manifest_tag
            ):
                errors.append(
                    "Manifest is not using the "
                    "IMS Common Cartridge 1.1 namespace."
                )
            else:
                results.append(
                    "IMS Common Cartridge namespace passed"
                )

            # =============================================
            # MANIFEST METADATA
            # =============================================

            schema = manifest_root.find(
                ".//cc:schema",
                MANIFEST_NS,
            )

            schema_version = (
                manifest_root.find(
                    ".//cc:schemaversion",
                    MANIFEST_NS,
                )
            )

            if (
                schema is None
                or schema.text != "IMS Content"
            ):
                errors.append(
                    "Manifest schema is not IMS Content."
                )
            else:
                results.append(
                    "Manifest schema = IMS Content"
                )

            if (
                schema_version is None
                or schema_version.text
                != "1.1.3"
            ):
                errors.append(
                    "Manifest schemaversion "
                    "is not 1.1.3."
                )
            else:
                results.append(
                    "Manifest version = 1.1.3"
                )

            # =============================================
            # MANIFEST RESOURCES
            # =============================================

            resources = manifest_root.findall(
                ".//cc:resource",
                MANIFEST_NS,
            )

            qti_resources = [
                resource
                for resource in resources
                if resource.attrib.get(
                    "type"
                )
                == "imsqti_xmlv1p2"
            ]

            meta_resources = [
                resource
                for resource in resources
                if resource.attrib.get(
                    "type"
                )
                == (
                    "associatedcontent/"
                    "imscc_xmlv1p1/"
                    "learning-application-resource"
                )
            ]

            if len(qti_resources) != 1:
                errors.append(
                    "Expected one QTI resource "
                    f"but found {len(qti_resources)}."
                )
            else:
                results.append(
                    "One QTI manifest resource found"
                )

            if len(meta_resources) != 1:
                errors.append(
                    "Expected one Canvas metadata resource "
                    f"but found {len(meta_resources)}."
                )
            else:
                results.append(
                    "One metadata manifest resource found"
                )

            if (
                len(qti_resources) == 1
                and len(meta_resources) == 1
            ):

                qti_resource = (
                    qti_resources[0]
                )

                meta_resource = (
                    meta_resources[0]
                )

                meta_ident = (
                    meta_resource.attrib.get(
                        "identifier"
                    )
                )

                dependency = (
                    qti_resource.find(
                        "cc:dependency",
                        MANIFEST_NS,
                    )
                )

                if (
                    dependency is None
                    or dependency.attrib.get(
                        "identifierref"
                    )
                    != meta_ident
                ):
                    errors.append(
                        "QTI resource dependency does "
                        "not reference assessment metadata."
                    )
                else:
                    results.append(
                        "Assessment metadata dependency passed"
                    )

            # =============================================
            # MANIFEST FILE PATHS
            # =============================================

            manifest_files = []

            for element in manifest_root.findall(
                ".//cc:file",
                MANIFEST_NS,
            ):

                href = element.attrib.get(
                    "href"
                )

                if href:
                    manifest_files.append(
                        href
                    )

            if (
                assessment_relative
                not in manifest_files
            ):
                errors.append(
                    "Manifest does not reference "
                    "the assessment XML path."
                )
            else:
                results.append(
                    "Manifest references assessment XML"
                )

            if (
                meta_relative
                not in manifest_files
            ):
                errors.append(
                    "Manifest does not reference "
                    "assessment_meta.xml."
                )
            else:
                results.append(
                    "Manifest references assessment metadata"
                )

            for path in manifest_files:

                if path not in names:
                    errors.append(
                        "Manifest references missing file: "
                        f"{path}"
                    )

            # =============================================
            # CANVAS META NAMESPACE
            # =============================================

            expected_meta_tag = (
                "{"
                + CANVAS_NS["canvas"]
                + "}quiz"
            )

            if (
                meta_root.tag
                != expected_meta_tag
            ):
                errors.append(
                    "assessment_meta.xml is not "
                    "using Canvas cccv1p0 namespace."
                )
            else:
                results.append(
                    "Canvas assessment metadata "
                    "namespace passed"
                )

            # =============================================
            # META POINTS
            # =============================================

            points_element = meta_root.find(
                "canvas:points_possible",
                CANVAS_NS,
            )

            meta_points = numeric_text(
                points_element
            )

            if meta_points is None:
                errors.append(
                    "Canvas metadata is missing "
                    "points_possible."
                )
            else:
                results.append(
                    "Canvas points_possible found: "
                    f"{meta_points:g}"
                )

            # =============================================
            # ASSESSMENT STRUCTURE
            # =============================================

            assessment = assessment_root.find(
                "qti:assessment",
                QTI_NS,
            )

            if assessment is None:
                errors.append(
                    "Assessment element is missing."
                )

                return (
                    results,
                    errors,
                    warnings,
                )

            results.append(
                "QTI assessment element found"
            )

            section = assessment.find(
                "qti:section",
                QTI_NS,
            )

            if section is None:
                errors.append(
                    "root_section is missing."
                )

                return (
                    results,
                    errors,
                    warnings,
                )

            results.append(
                "QTI section found"
            )

            items = section.findall(
                "qti:item",
                QTI_NS,
            )

            results.append(
                f"Assessment contains "
                f"{len(items)} question(s)"
            )

            if (
                expected_questions is not None
                and len(items)
                != expected_questions
            ):
                errors.append(
                    f"Expected {expected_questions} "
                    f"questions but found "
                    f"{len(items)}."
                )

            # =============================================
            # QUESTION VALIDATION
            # =============================================

            total_points = 0.0

            numeric_count = 0

            allowed_types = {
                "multiple_choice_question",
                "multiple_answers_question",
                "numerical_question",
            }

            for item_index, item in enumerate(
                items,
                start=1,
            ):

                title = item.attrib.get(
                    "title"
                ) or f"Item {item_index}"

                question_type = metadata_value(
                    item,
                    "question_type",
                )

                if (
                    question_type
                    not in allowed_types
                ):
                    errors.append(
                        f"{title}: unsupported "
                        f"question_type "
                        f"{question_type!r}."
                    )

                    continue

                # -----------------------------------------
                # REQUIRED CANVAS METADATA
                # -----------------------------------------

                required_metadata = [
                    "question_type",
                    "points_possible",
                    "original_answer_ids",
                    "assessment_question_identifierref",
                    "calculator_type",
                ]

                for field_name in required_metadata:

                    value = metadata_value(
                        item,
                        field_name,
                    )

                    if (
                        value is None
                        and field_name
                        != "original_answer_ids"
                    ):
                        errors.append(
                            f"{title}: missing "
                            f"{field_name}."
                        )

                points_value = metadata_value(
                    item,
                    "points_possible",
                )

                try:
                    total_points += float(
                        points_value or 0
                    )
                except ValueError:
                    errors.append(
                        f"{title}: invalid "
                        "points_possible."
                    )

                # -----------------------------------------
                # MULTIPLE CHOICE
                # -----------------------------------------

                if (
                    question_type
                    == "multiple_choice_question"
                ):

                    response = item.find(
                        ".//qti:response_lid",
                        QTI_NS,
                    )

                    if response is None:
                        errors.append(
                            f"{title}: missing "
                            "response_lid."
                        )

                    elif (
                        response.attrib.get(
                            "rcardinality"
                        )
                        != "Single"
                    ):
                        errors.append(
                            f"{title}: Multiple Choice "
                            "must use Single cardinality."
                        )

                # -----------------------------------------
                # MULTIPLE ANSWER
                # -----------------------------------------

                elif (
                    question_type
                    == "multiple_answers_question"
                ):

                    response = item.find(
                        ".//qti:response_lid",
                        QTI_NS,
                    )

                    if response is None:
                        errors.append(
                            f"{title}: missing "
                            "response_lid."
                        )

                    elif (
                        response.attrib.get(
                            "rcardinality"
                        )
                        != "Multiple"
                    ):
                        errors.append(
                            f"{title}: Multiple Answer "
                            "must use Multiple cardinality."
                        )

                # -----------------------------------------
                # NUMERIC
                # -----------------------------------------

                elif (
                    question_type
                    == "numerical_question"
                ):

                    numeric_count += 1

                    response = item.find(
                        ".//qti:response_str",
                        QTI_NS,
                    )

                    if response is None:
                        errors.append(
                            f"{title}: missing "
                            "response_str."
                        )

                        continue

                    if (
                        response.attrib.get(
                            "rcardinality"
                        )
                        != "Single"
                    ):
                        errors.append(
                            f"{title}: numeric response "
                            "must use Single cardinality."
                        )

                    render_fib = response.find(
                        "qti:render_fib",
                        QTI_NS,
                    )

                    if render_fib is None:
                        errors.append(
                            f"{title}: missing "
                            "render_fib."
                        )

                        continue

                    if (
                        render_fib.attrib.get(
                            "fibtype"
                        )
                        != "Decimal"
                    ):
                        errors.append(
                            f"{title}: numeric render_fib "
                            "must use Decimal."
                        )

                    response_label = (
                        render_fib.find(
                            "qti:response_label",
                            QTI_NS,
                        )
                    )

                    if response_label is None:
                        errors.append(
                            f"{title}: numeric response "
                            "label is missing."
                        )

                    # Canvas-style margin.
                    varequal = item.find(
                        ".//qti:varequal"
                        "[@margintype='absolute']",
                        QTI_NS,
                    )

                    if varequal is None:
                        errors.append(
                            f"{title}: Canvas absolute "
                            "numeric margin is missing."
                        )

                    else:

                        margin = (
                            varequal.attrib.get(
                                "margin"
                            )
                        )

                        if margin is None:
                            errors.append(
                                f"{title}: numeric margin "
                                "value is missing."
                            )

                    low = item.find(
                        ".//qti:vargte",
                        QTI_NS,
                    )

                    high = item.find(
                        ".//qti:varlte",
                        QTI_NS,
                    )

                    if (
                        low is None
                        or high is None
                    ):
                        errors.append(
                            f"{title}: numeric low/high "
                            "range is incomplete."
                        )

            # =============================================
            # POINT TOTAL
            # =============================================

            if (
                meta_points is not None
                and abs(
                    total_points
                    - meta_points
                )
                > 0.0001
            ):
                errors.append(
                    "Question points total "
                    f"({total_points:g}) does not match "
                    "assessment_meta.xml "
                    f"({meta_points:g})."
                )
            else:
                results.append(
                    "Question points match "
                    "assessment metadata"
                )

            results.append(
                f"Checked {numeric_count} "
                "numeric question(s)"
            )

    return results, errors, warnings