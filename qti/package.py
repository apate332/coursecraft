import os
import tempfile
import uuid
import zipfile

from qti.generator import generate_assessment_xml
from qti.assessment_meta import generate_assessment_meta_xml


def generate_manifest_xml(
    assessment_id,
    metadata_id,
):
    return f"""<?xml version="1.0" encoding="UTF-8"?>

<manifest
    identifier="coursecraft_manifest"
    xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
    xmlns:imsqti="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">

    <organizations/>

    <resources>

        <resource
            identifier="{assessment_id}_resource"
            type="imsqti_xmlv1p2"
            href="{assessment_id}/{assessment_id}.xml">

            <file
                href="{assessment_id}/{assessment_id}.xml"/>

            <dependency
                identifierref="{metadata_id}"/>

        </resource>


        <resource
            identifier="{metadata_id}"
            type="associatedcontent/imscc_xmlv1p1/learning-application-resource"
            href="{assessment_id}/assessment_meta.xml">

            <file
                href="{assessment_id}/assessment_meta.xml"/>

        </resource>

    </resources>

</manifest>
"""


def create_qti_package(
    quiz_data,
    output_path,
):

    # -----------------------------------------------------
    # UNIQUE IDS
    # -----------------------------------------------------

    unique_id = uuid.uuid4().hex

    assessment_id = (
        f"assessment_{unique_id}"
    )

    metadata_id = (
        f"{assessment_id}_meta"
    )


    # -----------------------------------------------------
    # GENERATE XML
    # -----------------------------------------------------

    assessment_xml = (
        generate_assessment_xml(
            quiz_data
        )
    )

    assessment_meta_xml = (
        generate_assessment_meta_xml(
            quiz_data,
            assessment_id,
        )
    )

    manifest_xml = (
        generate_manifest_xml(
            assessment_id,
            metadata_id,
        )
    )


    # -----------------------------------------------------
    # TEMPORARY PACKAGE DIRECTORY
    # -----------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        assessment_dir = os.path.join(
            temp_dir,
            assessment_id,
        )

        os.makedirs(
            assessment_dir,
            exist_ok=True,
        )


        # -------------------------------------------------
        # ASSESSMENT XML
        # -------------------------------------------------

        assessment_path = os.path.join(
            assessment_dir,
            f"{assessment_id}.xml",
        )

        with open(
            assessment_path,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(
                assessment_xml
            )


        # -------------------------------------------------
        # ASSESSMENT METADATA
        # -------------------------------------------------

        metadata_path = os.path.join(
            assessment_dir,
            "assessment_meta.xml",
        )

        with open(
            metadata_path,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(
                assessment_meta_xml
            )


        # -------------------------------------------------
        # MANIFEST
        # -------------------------------------------------

        manifest_path = os.path.join(
            temp_dir,
            "imsmanifest.xml",
        )

        with open(
            manifest_path,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(
                manifest_xml
            )


        # -------------------------------------------------
        # CREATE ZIP
        # -------------------------------------------------

        with zipfile.ZipFile(
            output_path,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as package:

            package.write(
                manifest_path,
                "imsmanifest.xml",
            )

            package.write(
                assessment_path,
                (
                    f"{assessment_id}/"
                    f"{assessment_id}.xml"
                ),
            )

            package.write(
                metadata_path,
                (
                    f"{assessment_id}/"
                    "assessment_meta.xml"
                ),
            )