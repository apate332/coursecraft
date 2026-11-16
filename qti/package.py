import hashlib
import html
import os
import tempfile
import uuid
import zipfile
from datetime import date

from quiz.normalizer import normalize_quiz
from qti.generator import generate_assessment_xml
from qti.assessment_meta import generate_assessment_meta_xml


# =========================================================
# HELPERS
# =========================================================

def xml_escape(value):
    if value is None:
        return ""

    return html.escape(
        str(value),
        quote=True,
    )


def random_ident():
    """
    Generate a Canvas-style identifier.
    """

    return "g" + uuid.uuid4().hex


def hash_ident(value):
    """
    Generate a stable identifier from another identifier.
    """

    digest = hashlib.md5(
        str(value).encode("utf-8")
    ).hexdigest()

    return "g" + digest


# =========================================================
# IMS COMMON CARTRIDGE MANIFEST
# =========================================================

def generate_manifest_xml(
    quiz_ident,
    meta_ident,
    package_title,
):
    """
    Build the IMS Common Cartridge manifest used by
    Canvas-style New Quiz QTI packages.
    """

    today = date.today().isoformat()

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest
    identifier="{random_ident()}"
    xmlns="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1"
    xmlns:lom="http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource"
    xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="
        http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1
        http://www.imsglobal.org/xsd/imscp_v1p1.xsd
        http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource
        http://www.imsglobal.org/profile/cc/ccv1p1/LOM/ccv1p1_lomresource_v1p0.xsd
        http://www.imsglobal.org/xsd/imsmd_v1p2
        http://www.imsglobal.org/xsd/imsmd_v1p2p2.xsd">

  <metadata>

    <schema>IMS Content</schema>

    <schemaversion>1.1.3</schemaversion>

    <imsmd:lom>

      <imsmd:general>

        <imsmd:title>

          <imsmd:string>{xml_escape(package_title)}</imsmd:string>

        </imsmd:title>

      </imsmd:general>

      <imsmd:lifeCycle>

        <imsmd:contribute>

          <imsmd:date>

            <imsmd:dateTime>{today}</imsmd:dateTime>

          </imsmd:date>

        </imsmd:contribute>

      </imsmd:lifeCycle>

    </imsmd:lom>

  </metadata>

  <organizations/>

  <resources>

    <resource
        identifier="{quiz_ident}"
        type="imsqti_xmlv1p2">

      <file
          href="{quiz_ident}/{quiz_ident}.xml"/>

      <dependency
          identifierref="{meta_ident}"/>

    </resource>

    <resource
        identifier="{meta_ident}"
        type="associatedcontent/imscc_xmlv1p1/learning-application-resource"
        href="{quiz_ident}/assessment_meta.xml">

      <file
          href="{quiz_ident}/assessment_meta.xml"/>

    </resource>

  </resources>

</manifest>
"""


# =========================================================
# PACKAGE BUILDER
# =========================================================

def create_qti_package(
    quiz_data,
    output_path,
    settings=None,
):
    """
    Build a Canvas-style QTI package for New Quizzes.

    Structure:

        imsmanifest.xml

        <quiz_ident>/
            <quiz_ident>.xml
            assessment_meta.xml

        non_cc_assessments/

    The quiz is normalized before export so obvious
    AI structural inconsistencies are corrected before
    Canvas serialization.
    """

    # -----------------------------------------------------
    # NORMALIZE QUIZ
    # -----------------------------------------------------

    quiz_data = normalize_quiz(
        quiz_data
    )

    # -----------------------------------------------------
    # IDENTIFIERS
    # -----------------------------------------------------

    quiz_ident = random_ident()

    meta_ident = hash_ident(
        f"{quiz_ident}:meta"
    )

    # -----------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------

    final_settings = {
        "description": "",
        "shuffle_questions": False,
        "shuffle_answers": False,
        "show_correct_answers": False,
        "allowed_attempts": 1,
        "one_question_at_a_time": False,
        "cant_go_back": False,
        "calculator": "none",
    }

    if settings:
        final_settings.update(
            settings
        )

    # -----------------------------------------------------
    # GENERATE XML
    # -----------------------------------------------------

    assessment_xml = generate_assessment_xml(
        quiz_data,
        quiz_ident=quiz_ident,
        settings=final_settings,
    )

    assessment_meta_xml = (
        generate_assessment_meta_xml(
            quiz_data,
            quiz_ident,
            settings=final_settings,
        )
    )

    manifest_xml = generate_manifest_xml(
        quiz_ident,
        meta_ident,
        quiz_data.get(
            "title",
            "CourseCraft Quiz",
        ),
    )

    # -----------------------------------------------------
    # BUILD TEMPORARY PACKAGE
    # -----------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        # -------------------------------------------------
        # QUIZ DIRECTORY
        # -------------------------------------------------

        quiz_dir = os.path.join(
            temp_dir,
            quiz_ident,
        )

        os.makedirs(
            quiz_dir,
            exist_ok=True,
        )

        # -------------------------------------------------
        # NON-CC ASSESSMENTS DIRECTORY
        # -------------------------------------------------

        non_cc_dir = os.path.join(
            temp_dir,
            "non_cc_assessments",
        )

        os.makedirs(
            non_cc_dir,
            exist_ok=True,
        )

        # -------------------------------------------------
        # ASSESSMENT XML
        # -------------------------------------------------

        assessment_path = os.path.join(
            quiz_dir,
            f"{quiz_ident}.xml",
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
        # ASSESSMENT META
        # -------------------------------------------------

        meta_path = os.path.join(
            quiz_dir,
            "assessment_meta.xml",
        )

        with open(
            meta_path,
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
        # ZIP
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
                    f"{quiz_ident}/"
                    f"{quiz_ident}.xml"
                ),
            )

            package.write(
                meta_path,
                (
                    f"{quiz_ident}/"
                    "assessment_meta.xml"
                ),
            )

            # Explicitly create the empty folder.
            package.writestr(
                "non_cc_assessments/",
                "",
            )

    return {
        "output_path": output_path,
        "quiz_ident": quiz_ident,
        "meta_ident": meta_ident,
        "questions": len(
            quiz_data.get(
                "questions",
                [],
            )
        ),
    }