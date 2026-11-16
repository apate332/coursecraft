import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET


QTI_NS = {
    "qti": "http://www.imsglobal.org/xsd/ims_qtiasiv1p2",
}

MANIFEST_NS = {
    "ims": "http://www.imsglobal.org/xsd/imscp_v1p1",
}


def validate_qti_package(zip_path, expected_questions=None):
    """
    Validate the basic structure of a CourseCraft QTI package.

    This does NOT guarantee Canvas will accept the package.
    It catches structural problems before Canvas testing.
    """

    results = []
    errors = []

    # -----------------------------------------------------
    # ZIP
    # -----------------------------------------------------

    if not os.path.exists(zip_path):
        raise FileNotFoundError(
            f"Package not found: {zip_path}"
        )

    if not zipfile.is_zipfile(zip_path):
        raise ValueError(
            f"Not a valid ZIP file: {zip_path}"
        )

    results.append("✓ Valid ZIP file")

    # -----------------------------------------------------
    # EXTRACT
    # -----------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        with zipfile.ZipFile(zip_path, "r") as package:
            package.extractall(temp_dir)

            zip_files = package.namelist()

        # -------------------------------------------------
        # MANIFEST
        # -------------------------------------------------

        manifest_path = os.path.join(
            temp_dir,
            "imsmanifest.xml",
        )

        if not os.path.exists(manifest_path):
            errors.append("Missing imsmanifest.xml")
        else:
            results.append("✓ imsmanifest.xml found")

        assessment_files = [
            name
            for name in zip_files
            if name.endswith(".xml")
            and not name.endswith("imsmanifest.xml")
            and not name.endswith("assessment_meta.xml")
        ]

        metadata_files = [
            name
            for name in zip_files
            if name.endswith("assessment_meta.xml")
        ]

        if len(assessment_files) != 1:
            errors.append(
                "Expected exactly one assessment XML file; "
                f"found {len(assessment_files)}"
            )
        else:
            results.append(
                "✓ One assessment XML file found"
            )

        if len(metadata_files) != 1:
            errors.append(
                "Expected exactly one assessment_meta.xml; "
                f"found {len(metadata_files)}"
            )
        else:
            results.append(
                "✓ assessment_meta.xml found"
            )

        if errors:
            return results, errors

        assessment_relative = assessment_files[0]
        metadata_relative = metadata_files[0]

        assessment_path = os.path.join(
            temp_dir,
            assessment_relative,
        )

        metadata_path = os.path.join(
            temp_dir,
            metadata_relative,
        )

        # -------------------------------------------------
        # PARSE XML
        # -------------------------------------------------

        try:
            manifest_tree = ET.parse(
                manifest_path
            )
            results.append(
                "✓ Manifest XML is well formed"
            )
        except ET.ParseError as error:
            errors.append(
                f"Manifest XML error: {error}"
            )
            return results, errors

        try:
            assessment_tree = ET.parse(
                assessment_path
            )
            results.append(
                "✓ Assessment XML is well formed"
            )
        except ET.ParseError as error:
            errors.append(
                f"Assessment XML error: {error}"
            )
            return results, errors

        try:
            ET.parse(metadata_path)
            results.append(
                "✓ Assessment metadata XML is well formed"
            )
        except ET.ParseError as error:
            errors.append(
                f"assessment_meta.xml error: {error}"
            )

        # -------------------------------------------------
        # MANIFEST REFERENCES
        # -------------------------------------------------

        manifest_root = manifest_tree.getroot()

        file_elements = manifest_root.findall(
            ".//ims:file",
            MANIFEST_NS,
        )

        manifest_files = {
            element.attrib.get("href")
            for element in file_elements
            if element.attrib.get("href")
        }

        if assessment_relative in manifest_files:
            results.append(
                "✓ Manifest references assessment XML"
            )
        else:
            errors.append(
                "Manifest does not reference assessment XML"
            )

        if metadata_relative in manifest_files:
            results.append(
                "✓ Manifest references assessment_meta.xml"
            )
        else:
            errors.append(
                "Manifest does not reference assessment_meta.xml"
            )

        # -------------------------------------------------
        # ASSESSMENT STRUCTURE
        # -------------------------------------------------

        assessment_root = assessment_tree.getroot()

        sections = assessment_root.findall(
            ".//qti:section",
            QTI_NS,
        )

        if not sections:
            errors.append(
                "Assessment contains no QTI section"
            )
        else:
            results.append(
                "✓ Assessment contains a section"
            )

        items = assessment_root.findall(
            ".//qti:item",
            QTI_NS,
        )

        results.append(
            f"✓ Assessment contains {len(items)} question(s)"
        )

        if (
            expected_questions is not None
            and len(items) != expected_questions
        ):
            errors.append(
                f"Expected {expected_questions} questions "
                f"but found {len(items)}"
            )

        # -------------------------------------------------
        # QUESTION TYPES
        # -------------------------------------------------

        question_types = []

        for item in items:

            metadata_fields = item.findall(
                ".//qti:qtimetadatafield",
                QTI_NS,
            )

            item_type = None

            for field in metadata_fields:

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
                    and entry is not None
                    and label.text == "question_type"
                ):
                    item_type = entry.text
                    break

            question_types.append(item_type)

        allowed_types = {
            "multiple_choice_question",
            "multiple_answers_question",
            "numerical_question",
        }

        for index, question_type in enumerate(
            question_types,
            start=1,
        ):

            if question_type not in allowed_types:
                errors.append(
                    f"Item {index} has unsupported or missing "
                    f"question_type: {question_type}"
                )

        if not any(
            question_type not in allowed_types
            for question_type in question_types
        ):
            results.append(
                "✓ All question types are recognized"
            )

        # -------------------------------------------------
        # MULTIPLE CHOICE
        # -------------------------------------------------

        for item in items:

            title = item.attrib.get(
                "title",
                "Unknown question",
            )

            response_lid = item.find(
                ".//qti:response_lid",
                QTI_NS,
            )

            if response_lid is None:
                continue

            cardinality = response_lid.attrib.get(
                "rcardinality"
            )

            item_xml = ET.tostring(
                item,
                encoding="unicode",
            )

            if (
                "multiple_choice_question"
                in item_xml
            ):

                if cardinality != "Single":
                    errors.append(
                        f"{title}: Multiple Choice must "
                        "use rcardinality='Single'"
                    )

            if (
                "multiple_answers_question"
                in item_xml
            ):

                if cardinality != "Multiple":
                    errors.append(
                        f"{title}: Multiple Answer must "
                        "use rcardinality='Multiple'"
                    )

        results.append(
            "✓ Choice-question cardinality checked"
        )

        # -------------------------------------------------
        # NUMERIC
        # -------------------------------------------------

        numeric_items = []

        for item in items:

            item_xml = ET.tostring(
                item,
                encoding="unicode",
            )

            if "numerical_question" in item_xml:
                numeric_items.append(item)

        for item in numeric_items:

            title = item.attrib.get(
                "title",
                "Numeric question",
            )

            response_str = item.find(
                ".//qti:response_str",
                QTI_NS,
            )

            if response_str is None:
                errors.append(
                    f"{title}: Numeric item has no response_str"
                )
                continue

            render_fib = response_str.find(
                "qti:render_fib",
                QTI_NS,
            )

            if render_fib is None:
                errors.append(
                    f"{title}: Numeric item has no render_fib"
                )
                continue

            response_label = render_fib.find(
                "qti:response_label",
                QTI_NS,
            )

            if response_label is None:
                errors.append(
                    f"{title}: Numeric item has no "
                    "response_label inside render_fib"
                )

        if numeric_items:
            results.append(
                f"✓ Checked {len(numeric_items)} numeric item(s)"
            )

    return results, errors