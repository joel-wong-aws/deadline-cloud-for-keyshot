# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import json
import os
import shutil
import tempfile
from unittest import mock

import pytest

from .. import lux_import_override  # noqa F401

# We can't use traditional imports due to spaces in the file name.
# The spaces are necessary because KeyShot uses the file name as the script name.
deadline = __import__("deadline.keyshot_submitter.Submit to AWS Deadline Cloud")
submitter = getattr(deadline.keyshot_submitter, "Submit to AWS Deadline Cloud")


@pytest.fixture
def mock_lux_is_scene_changed():
    with mock.patch.object(submitter.lux, "isSceneChanged") as is_scene_changed_mock:
        yield is_scene_changed_mock


@pytest.fixture
def mock_lux_get_input_dialog():
    with mock.patch.object(submitter.lux, "getInputDialog") as get_input_dialog_mock:
        yield get_input_dialog_mock


@pytest.fixture
def mock_lux_save_file():
    with mock.patch.object(submitter.lux, "saveFile") as save_file_mock:
        yield save_file_mock


@pytest.fixture
def mock_lux_save_package():
    with mock.patch.object(submitter.lux, "savePackage") as save_package_mock:
        yield save_package_mock


@pytest.fixture
def mock_lux_is_paused():
    with mock.patch.object(submitter.lux, "isPaused") as is_paused_mock:
        yield is_paused_mock


@pytest.fixture
def mock_lux_pause():
    with mock.patch.object(submitter.lux, "pause") as pause_mock:
        yield pause_mock


@pytest.fixture
def mock_lux_unpause():
    with mock.patch.object(submitter.lux, "unpause") as unpause_mock:
        yield unpause_mock


def test_construct_job_template():
    filename = "test_filename"

    job_template = submitter.construct_job_template(filename)

    assert job_template["name"] == filename


def test_construct_asset_references():
    settings = submitter.Settings(
        parameter_values=[
            {"name": "KeyShotFile", "value": "test_scene_file"},
            {"name": "OutputFilePath", "value": r"test_scene_file.%d.png"},
            {"name": "OutputFormat", "value": "PNG"},
            {"name": "Frames", "value": "10-17"},
        ],
        input_filenames=["test_filename_1"],
        auto_detected_input_filenames=["test_filename_2"],
        input_directories=["test_directory_1", "test_directory_2"],
        output_directories=["test_directory_3"],
        referenced_paths=["reference_path_1", "reference_path_2"],
    )

    asset_references = submitter.construct_asset_references(settings)

    assert asset_references["assetReferences"]["inputs"]["filenames"] == [
        "test_filename_1",
        "test_filename_2",
    ]
    assert (
        asset_references["assetReferences"]["inputs"]["directories"] == settings.input_directories
    )
    assert (
        asset_references["assetReferences"]["outputs"]["directories"] == settings.output_directories
    )
    assert asset_references["assetReferences"]["referencedPaths"] == settings.referenced_paths


def test_construct_parameter_values():
    settings = submitter.Settings(
        parameter_values=[
            {"name": "KeyShotFile", "value": "test_scene_file"},
            {"name": "OutputFilePath", "value": r"test_scene_file.%d.png"},
            {"name": "OutputFormat", "value": "PNG"},
            {"name": "Frames", "value": "10-17"},
        ],
        input_filenames=[],
        auto_detected_input_filenames=[],
        input_directories=[],
        output_directories=[],
        referenced_paths=[],
    )

    parameter_values = submitter.construct_parameter_values(settings)

    assert parameter_values == {
        "parameterValues": [
            {"name": "KeyShotFile", "value": "test_scene_file"},
            {"name": "OutputFilePath", "value": r"test_scene_file.%d.png"},
            {"name": "OutputFormat", "value": "PNG"},
            {"name": "Frames", "value": "10-17"},
        ]
    }


def test_settings_serialize_correctly():
    settings = submitter.Settings(
        parameter_values=[
            {"name": "KeyShotFile", "value": "test_scene_file"},
            {"name": "OutputFilePath", "value": r"test_scene_file.%d.png"},
            {"name": "OutputFormat", "value": "PNG"},
            {"name": "Frames", "value": "10-17"},
        ],
        input_filenames=["test_filename_1"],
        auto_detected_input_filenames=["test_directory_3"],
        input_directories=["test_directory_1"],
        output_directories=["test_directory_2"],
        referenced_paths=["test_ref_path"],
    )

    assert settings.output_sticky_settings() == {
        "parameterValues": [
            {"name": "OutputFilePath", "value": r"test_scene_file.%d.png"},
            {"name": "OutputFormat", "value": "PNG"},
            {"name": "Frames", "value": "10-17"},
        ],
        "inputFilenames": ["test_filename_1"],
        "inputDirectories": ["test_directory_1"],
        "outputDirectories": ["test_directory_2"],
        "referencedPaths": ["test_ref_path"],
    }


def test_settings_apply_sticky_settings():
    settings = submitter.Settings(
        parameter_values=[
            {"name": "KeyShotFile", "value": "test_scene_file"},
            {"name": "OutputFilePath", "value": r"test_scene_file.%d.png"},
            {"name": "OutputFormat", "value": "PNG"},
            {"name": "Frames", "value": "10-17"},
        ],
        input_filenames=["test_filename_1"],
        auto_detected_input_filenames=["test_filename_2"],
        input_directories=["test_directory_1"],
        output_directories=["test_directory_2"],
        referenced_paths=["test_ref_path"],
    )
    initial_settings = settings.output_sticky_settings()

    settings.apply_sticky_settings({})
    assert settings.output_sticky_settings() == initial_settings

    settings.apply_sticky_settings(
        {
            "parameterValues": [
                {"name": "OutputFilePath", "value": "test_output_2"},
                {"name": "OutputFormat", "value": "JPEG"},
                {"name": "Frames", "value": "20-27"},
            ],
            "inputFilenames": ["test_filename_10"],
            "inputDirectories": ["test_directory_11"],
            "outputDirectories": ["test_directory_12"],
            "referencedPaths": ["test_ref_path_2"],
        }
    )

    assert settings.parameter_values == [
        {"name": "KeyShotFile", "value": "test_scene_file"},
        {"name": "OutputFilePath", "value": "test_output_2"},
        {"name": "OutputFormat", "value": "JPEG"},
        {"name": "Frames", "value": "20-27"},
    ]
    assert settings.input_filenames == ["test_filename_10"]
    assert settings.input_directories == ["test_directory_11"]
    assert settings.output_directories == ["test_directory_12"]
    assert settings.referenced_paths == ["test_ref_path_2"]

    settings.apply_sticky_settings(
        {
            "parameterValues": [
                # Some parameters should not be sticky
                {"name": "KeyShotFile", "value": "scene_file_from_sticky_settings"},
                {"name": "CondaPackages", "value": "keyshot=2023.* keyshot-openjd=0.0.1"},
                {"name": "CondaChannels", "value": "conda-forge"},
            ],
            "inputFilenames": ["test_filename_20"],
            "inputDirectories": ["test_directory_21"],
            "outputDirectories": ["test_directory_22"],
            "referencedPaths": ["test_ref_path_3"],
        }
    )

    assert settings.parameter_values == [
        {"name": "KeyShotFile", "value": "test_scene_file"},
        {"name": "OutputFilePath", "value": "test_output_2"},
        {"name": "OutputFormat", "value": "JPEG"},
        {"name": "Frames", "value": "20-27"},
    ]
    assert settings.input_filenames == ["test_filename_20"]
    assert settings.input_directories == ["test_directory_21"]
    assert settings.output_directories == ["test_directory_22"]
    assert settings.referenced_paths == ["test_ref_path_3"]


def test_settings_apply_submitter_settings():
    settings = submitter.Settings(
        parameter_values=[
            {"name": "KeyShotFile", "value": "scene_file_from_scene"},
            {"name": "OutputFilePath", "value": r"test_scene_file.%d.png"},
            {"name": "OutputFormat", "value": "PNG"},
            {"name": "Frames", "value": "10-17"},
        ],
        input_filenames=["test_filename_1"],
        auto_detected_input_filenames=["test_filename_2"],
        input_directories=["test_directory_1"],
        output_directories=["test_directory_2"],
        referenced_paths=["test_ref_path"],
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        with open(
            os.path.join(temp_dir, "parameter_values.json"), "w", encoding="utf-8"
        ) as parameter_values_file:
            json.dump(
                {
                    "parameterValues": [
                        {"name": "KeyShotFile", "value": "scene_file_from_gui_submit"},
                        {"name": "Frames", "value": "20-27"},
                        {"name": "OutputFilePath", "value": "test_output_2"},
                        {"name": "OutputFormat", "value": "JPEG"},
                    ],
                },
                parameter_values_file,
            )
        with open(
            os.path.join(temp_dir, "asset_references.json"), "w", encoding="utf-8"
        ) as asset_references_file:
            json.dump(
                {
                    "assetReferences": {
                        "inputs": {
                            "filenames": [
                                "test_filename_1",
                                "test_filename_2",
                                "test_filename_3",
                            ],
                            "directories": ["test_directory_2"],
                        },
                        "outputs": {
                            "directories": [
                                "test_directory_2",
                                "test_directory_3",
                            ]
                        },
                        "referencedPaths": ["test_ref_path_2"],
                    },
                },
                asset_references_file,
            )
        settings.apply_submitter_settings({"jobHistoryBundleDirectory": temp_dir})

    assert settings.parameter_values == [
        {"name": "KeyShotFile", "value": "scene_file_from_gui_submit"},
        {"name": "Frames", "value": "20-27"},
        {"name": "OutputFilePath", "value": "test_output_2"},
        {"name": "OutputFormat", "value": "JPEG"},
    ]
    assert sorted(settings.input_filenames) == ["test_filename_1", "test_filename_3"]
    assert sorted(settings.input_directories) == ["test_directory_2"]
    assert sorted(settings.output_directories) == ["test_directory_2", "test_directory_3"]
    assert sorted(settings.referenced_paths) == ["test_ref_path_2"]


def test_unsaved_changes_prompt(
    mock_lux_is_scene_changed, mock_lux_get_input_dialog, mock_lux_save_file
):
    mock_lux_is_scene_changed.return_value = True
    mock_lux_get_input_dialog.return_value = None  # emulate clicking Cancel
    with pytest.raises(Exception):
        submitter.main()
    mock_lux_save_file.assert_not_called()

    mock_lux_get_input_dialog.return_value = {}  # emulate clicking Ok
    # Raise an exception so the main() handler exits after the file save operation is called.
    # We want to verify that the saveFile call is made, but don't want to run the rest of the
    # submitter.
    mock_lux_save_file.side_effect = Exception()
    with pytest.raises(Exception):
        submitter.main()
    mock_lux_save_file.assert_called()


def test_auto_pause_resume(
    mock_lux_is_paused, mock_lux_pause, mock_lux_unpause, mock_lux_is_scene_changed
):
    # Throw an exception to cut the submitter short
    mock_lux_is_scene_changed.side_effect = Exception()

    mock_lux_is_paused.return_value = True
    with pytest.raises(Exception):
        submitter.main()
    mock_lux_pause.assert_not_called()
    mock_lux_unpause.assert_not_called()

    mock_lux_is_paused.return_value = False
    with pytest.raises(Exception):
        submitter.main()
    mock_lux_pause.assert_called()
    mock_lux_unpause.assert_called()


def test_save_ksp_bundle(mock_lux_save_package):
    dir = os.path.normpath("/testdir/test")
    bundle_name = "test_bundle.ksp"
    expected_bundle_path = os.path.normpath(f"{dir}/{bundle_name}")

    output = submitter.save_ksp_bundle(dir, bundle_name)

    assert output == expected_bundle_path
    mock_lux_save_package.assert_called_once_with(path=expected_bundle_path)


def test_get_ksp_bundle_files():

    TEST_SCENE_FILE = "test_scene_file.bip"
    TEST_ASSET_FILE = "test_asset.png"
    TEST_KSP_BUNDLE_NAME = "test_ksp_bundle"

    with tempfile.TemporaryDirectory() as temp_dir:
        to_zip_dir = os.path.join(temp_dir, "to_zip")
        os.mkdir(to_zip_dir)
        with open(os.path.join(to_zip_dir, TEST_SCENE_FILE), "w", encoding="utf-8") as file:
            file.write("test scene")
        with open(os.path.join(to_zip_dir, TEST_ASSET_FILE), "w", encoding="utf-8") as file:
            file.write("test asset")

        # Creating a zip archive as that's what is used to unpack a ksp and a ksp
        # can't be created easily outside of KeyShot
        shutil.make_archive(os.path.join(temp_dir, TEST_KSP_BUNDLE_NAME), "zip", to_zip_dir)

        with mock.patch.object(
            submitter,
            "save_ksp_bundle",
            return_value=os.path.join(temp_dir, f"{TEST_KSP_BUNDLE_NAME}.zip"),
        ) as mock_save_ksp_bundle:
            scene_file, input_filenames = submitter.get_ksp_bundle_files(temp_dir)

        assert scene_file == os.path.join(temp_dir, "unpack", TEST_SCENE_FILE)
        assert len(input_filenames) == 1
        assert input_filenames[0] == os.path.join(temp_dir, "unpack", TEST_ASSET_FILE)
        mock_save_ksp_bundle.assert_called_once_with(os.path.join(temp_dir, "ksp"), mock.ANY)
