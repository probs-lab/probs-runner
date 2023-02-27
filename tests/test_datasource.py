# -*- coding: utf-8 -*-

from io import StringIO
import gzip
import re
from pathlib import Path
import pytest

from probs_runner import Datasource, load_datasource


class TestDatasourceCreatedManually:

    @pytest.fixture
    def datasource(self):
        return Datasource.from_facts(":Farming a :Process .")

    def test_has_load_data(self, datasource):
        match = re.match(r"import (.*)", datasource.load_data_script)
        assert match
        filename = f"data/{match.group(1)}"
        assert filename in datasource.input_files
        # check contents
        contents = datasource.input_files[filename].read()
        assert contents == ":Farming a :Process ."

    def test_has_no_load_rules(self, datasource):
        assert datasource.load_rules_script == ""


class TestDatasourceFromFolder:
    DATASOURCE_FOLDER = Path(__file__).parent / "sample_datasource_simple"

    @pytest.fixture
    def datasource(self):
        return load_datasource(self.DATASOURCE_FOLDER)

    def test_has_load_data(self, datasource):
        assert "prefix ufrd: <" in datasource.load_data_script
        assert "data.csv" in datasource.load_data_script

    def test_has_load_rules(self, datasource):
        assert "map.dlog" in datasource.load_rules_script

    def test_has_input_files(self, datasource):
        assert len(datasource.input_files) == 3  # data and 2 rules
        # target_path, source_path = list(datasource.input_files.items())[0]
        # assert source_path == self.DATASOURCE_FOLDER / "data.csv"
        # assert target_path.name == "data.csv"

        # Check datasource path matches setting for $(dir.datasource)
        # datasource_path = target_path.parent.name
        # assert datasource_path in datasource.load_data_script


class TestDatasourceFromSingleFile:
    def test_loads_data(self, tmp_path):
        p = tmp_path / "data.ttl"
        p.write_text(":Farming a :Process .\n")
        ds = load_datasource(p)
        assert 'import "$(dir.datasource)data.ttl"' in ds.load_data_script
        assert ds.load_rules_script == ""

    def test_loads_rules(self, tmp_path):
        p = tmp_path / "rules.dlog"
        a_rule = (":a[?x] :- :b[?x] .\n")
        p.write_text(a_rule)
        ds = load_datasource(p)
        assert 'import' not in ds.load_data_script
        assert 'rules.dlog' in ds.load_rules_script


class TestDatasourceFromFilesCustomLoadDataScript:
    DATASOURCE_FOLDER = Path(__file__).parent / "sample_datasource_simple"

    def test_raises_error_for_csv_without_load_script(self):
        with pytest.raises(ValueError, match=r"cannot automatically load some files: data.csv"):
            Datasource.from_files([self.DATASOURCE_FOLDER / "data.csv"])

    def test_loads_csv_with_load_script(self):
        input_file = self.DATASOURCE_FOLDER / "data.csv"
        load_data_script = self.DATASOURCE_FOLDER / "load_data.rdfox"
        ds = Datasource.from_files([input_file], load_data_script)

        keys = list(ds.input_files.keys())
        assert len(keys) == 1
        target_path = keys[0]
        assert target_path.name == "data.csv"
        assert ds.input_files[target_path] == input_file

        assert ds.load_data_script.endswith(load_data_script.read_text())

    def test_loads_csv_with_multiple_load_script(self):
        input_file = self.DATASOURCE_FOLDER / "data.csv"
        load_data_script_1 = self.DATASOURCE_FOLDER / "load_data.rdfox"
        load_data_script_2 = self.DATASOURCE_FOLDER / "load_data_2.rdfox"
        ds = Datasource.from_files(
            [input_file], [load_data_script_1, load_data_script_2]
        )

        assert load_data_script_1.read_text() in ds.load_data_script
        assert load_data_script_2.read_text() in ds.load_data_script

    def test_loads_csv_with_multiple_rules(self):
        input_file = self.DATASOURCE_FOLDER / "data.csv"
        load_data_script = self.DATASOURCE_FOLDER / "load_data.rdfox"
        rules_1 = self.DATASOURCE_FOLDER / "map.dlog"
        rules_2 = self.DATASOURCE_FOLDER / "map_2.dlog"
        ds = Datasource.from_files(
            [input_file, rules_1, rules_2], load_data_script
        )
        assert "map.dlog" in ds.load_rules_script
        assert "map_2.dlog" in ds.load_rules_script

    def test_renames_input_files_with_dict(self):
        input_file = self.DATASOURCE_FOLDER / "data.csv"
        load_data_script = self.DATASOURCE_FOLDER / "load_data.rdfox"
        ds = Datasource.from_files({"something_else.csv": input_file},
                                   load_data_script)

        assert ds.input_files == {
            Path("data/something_else.csv"): input_file
        }

    def test_renames_input_files_with_dict_in_subdir(self):
        input_file = self.DATASOURCE_FOLDER / "data.csv"
        load_data_script = self.DATASOURCE_FOLDER / "load_data.rdfox"
        ds = Datasource.from_files({"something_else.csv": input_file},
                                   load_data_script, data_subdir="sub")

        assert ds.input_files == {
            Path("data/sub/something_else.csv"): input_file
        }

    def test_automatically_loads_ttl(self, tmp_path):
        p = tmp_path / "data.ttl"
        p.write_text(":Farming a :Process .\n")
        ds = Datasource.from_files([p])
        assert 'import "$(dir.datasource)data.ttl"' in ds.load_data_script
        assert ds.load_rules_script == ""

    def test_automatically_loads_nt_gz(self, tmp_path):
        p = tmp_path / "data.nt.gz"
        with gzip.open(p, "wt") as f:
            f.write(":Farming a :Process .\n")
        ds = Datasource.from_files([p])
        assert 'import "$(dir.datasource)data.nt.gz"' in ds.load_data_script
        assert ds.load_rules_script == ""


def test_datasource_from_files_accepts_str():
    a = Datasource.from_files(["a.ttl"])
    b = Datasource.from_files([Path("a.ttl")])
    assert a == b


def test_datasource_target_paths_are_unique():
    a = Datasource.from_files(["path1/x.ttl"])
    b = Datasource.from_files(["path2/x.ttl"])
    assert a.input_files != b.input_files


def test_datasource_reuses_same_path_with_different_load_data_scripts():
    a = Datasource.from_files(["a.csv"], load_data_script=StringIO("a"))
    b = Datasource.from_files(["a.csv"], load_data_script=StringIO("b"))
    assert a.input_files == b.input_files
    assert a != b


def test_datasource_reuses_same_path_with_different_load_rules_scripts():
    a = Datasource.from_files(["a.ttl"], load_rules_script=StringIO("a"))
    b = Datasource.from_files(["a.ttl"], load_rules_script=StringIO("b"))
    assert a.input_files == b.input_files
    assert a != b


def test_datasource_errors_for_missing_folder():
    with pytest.raises(FileNotFoundError):
        load_datasource(Path("MISSING_FOLDER"))


def test_datasource_raises_error_for_file_objects_in_list(tmp_path):
    p = tmp_path / "data.ttl"
    p.write_text(":Farming a :Process .\n")
    with pytest.raises(ValueError):
        with open(p) as f:
            a = Datasource.from_files([f])


def test_datasource_accepts_file_objects_in_dict(tmp_path):
    p = tmp_path / "data.ttl"
    p.write_text(":Farming a :Process .\n")
    with open(p) as f:
        a = Datasource.from_files({"data.ttl": f})
