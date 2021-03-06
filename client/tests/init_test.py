# Copyright (c) 2016-present, Facebook, Inc.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from unittest.mock import MagicMock, patch

from .. import EnvironmentException, buck, find_project_root, resolve_source_directories


class InitTest(unittest.TestCase):
    @patch("os.path.isfile")
    def test_find_configuration(self, os_mock_isfile) -> None:
        os_mock_isfile.side_effect = [False, False, False, True]
        self.assertEqual(find_project_root("/a/b/c/d"), "/a")
        os_mock_isfile.side_effect = [True]
        self.assertEqual(find_project_root("/a"), "/a")
        os_mock_isfile.side_effect = [False, False]
        self.assertEqual(find_project_root("/a/b"), "/a/b")

    @patch("os.path.realpath", side_effect=lambda path: "realpath({})".format(path))
    @patch("os.getcwd", return_value="/")
    @patch("os.path.exists", return_value=True)
    def test_resolve_source_directories(self, realpath, cwd, exists) -> None:
        arguments = MagicMock()
        arguments.source_directory = []
        arguments.original_directory = "/root"
        arguments.use_buck_cache = False
        arguments.build = False
        configuration = MagicMock()
        configuration.source_directories = []

        with self.assertRaises(EnvironmentException):
            resolve_source_directories(arguments, configuration)

        # Arguments override configuration.
        with patch.object(
            buck, "generate_source_directories", return_value=[]
        ) as buck_source_directories:
            arguments.source_directory = ["arguments_source_directory"]
            configuration.source_directories = ["configuration_source_directory"]

            source_directories = resolve_source_directories(arguments, configuration)
            buck_source_directories.assert_called_with(
                set(), build=False, prompt=True, use_cache=False
            )
            self.assertEqual(
                source_directories, {"realpath(root/arguments_source_directory)"}
            )

        with patch.object(
            buck, "generate_source_directories", return_value=["arguments_target"]
        ) as buck_source_directories:
            arguments.source_directory = []
            arguments.target = ["arguments_target"]
            configuration.source_directories = ["configuration_source_directory"]

            source_directories = resolve_source_directories(arguments, configuration)
            buck_source_directories.assert_called_with(
                {"arguments_target"}, build=False, prompt=True, use_cache=False
            )
            self.assertEqual(source_directories, {"realpath(root/arguments_target)"})

        # Configuration is picked up when no arguments provided.
        with patch.object(
            buck, "generate_source_directories", return_value=[]
        ) as buck_source_directories:
            arguments.source_directory = []
            arguments.target = []
            arguments.build = True
            configuration.targets = ["configuration_target"]
            configuration.source_directories = ["configuration_source_directory"]

            source_directories = resolve_source_directories(arguments, configuration)
            buck_source_directories.assert_called_with(
                {"configuration_target"}, build=True, prompt=True, use_cache=False
            )
            self.assertEqual(
                source_directories, {"realpath(root/configuration_source_directory)"}
            )

        # Files are translated relative to project root
        with patch.object(
            buck, "generate_source_directories", return_value=[]
        ) as buck_source_directories:
            arguments.source_directory = []
            arguments.target = []
            configuration.source_directories = ["."]
            source_directories = resolve_source_directories(arguments, configuration)
            self.assertEqual(source_directories, {"realpath(root/.)"})
