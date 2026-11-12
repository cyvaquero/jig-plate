"""Unit tests for jig-plate.py -- the CLI entry point.

Nothing in test_jig_plate_base.py exercises this file: not stamp() (the
80-byte binary STL header, and the truncation fix from 2.4.10 that keeps
a header >= 80 bytes from silently corrupting the file), not main()'s
end-to-end output (both STLs + all four diagrams, written into OUT_DIR/
IMG_DIR), and not the --label error path (a bad label should exit like
any other argparse error, not crash with a raw traceback).

A hyphenated filename can't be `import`ed directly, so the module is
loaded via importlib from its file path -- the same way any other
generator script would need to load it, since it isn't meant to be
imported (see jig_plate_base.py for the supported library entry point).
"""
import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "jig-plate.py"
_spec = importlib.util.spec_from_file_location("jig_plate_cli", _SCRIPT)
jig_plate_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jig_plate_cli)


class TestStamp:
    def test_pads_a_short_header_to_80_bytes_and_keeps_the_body_intact(self):
        body = b"body-bytes-that-must-not-move"

        data = jig_plate_cli.stamp(b"\x00" * 80 + body, "Jig plate 3.0.0")

        assert len(data) == 80 + len(body)
        header = data[:80]
        assert header[: len(b"Jig plate 3.0.0")] == b"Jig plate 3.0.0"
        assert header[len(b"Jig plate 3.0.0") :] == b"\x00" * (
            80 - len(b"Jig plate 3.0.0")
        )
        assert data[80:] == body

    def test_truncates_a_header_over_80_bytes_without_shifting_the_body(self):
        # the 2.4.10 fix: `.encode()[:80]` before `.ljust(80, ...)` --
        # without the [:80] slice, a >= 80 byte string assigned into
        # b[0:80] grows the bytearray instead of truncating, shifting
        # every later byte of the binary STL body and corrupting it.
        body = b"BODY-MUST-STAY-RIGHT-HERE"

        data = jig_plate_cli.stamp(b"\x00" * 80 + body, "x" * 200)

        assert len(data) == 80 + len(body), "body shifted -- file corrupted"
        assert data[:80] == b"x" * 80
        assert data[80:] == body


class TestWriteAtomic:
    def test_writes_bytes_to_a_new_path(self, tmp_path):
        target = tmp_path / "new.bin"
        jig_plate_cli.write_atomic(target, b"abc")
        assert target.read_bytes() == b"abc"
        assert [p.name for p in tmp_path.iterdir()] == ["new.bin"]

    def test_replaces_a_symlink_instead_of_following_it(self, tmp_path):
        sentinel = tmp_path / "sentinel.txt"
        sentinel.write_bytes(b"precious")
        target = tmp_path / "out.bin"
        target.symlink_to(sentinel)

        jig_plate_cli.write_atomic(target, b"new")

        assert sentinel.read_bytes() == b"precious"
        assert not target.is_symlink()
        assert target.read_bytes() == b"new"

    def test_a_failed_replace_leaves_no_temp_file_and_the_target_alone(
        self, tmp_path, monkeypatch
    ):
        target = tmp_path / "out.bin"
        target.write_bytes(b"old")

        def _boom(src, dst):
            raise OSError("replace failed")

        monkeypatch.setattr(jig_plate_cli.os, "replace", _boom)
        with pytest.raises(OSError, match="replace failed"):
            jig_plate_cli.write_atomic(target, b"new")

        assert target.read_bytes() == b"old"
        assert [p.name for p in tmp_path.iterdir()] == ["out.bin"]

    def test_a_failed_write_leaves_no_temp_file(self, tmp_path, monkeypatch):
        target = tmp_path / "out.bin"

        def _boom(path, mode):
            raise OSError("chmod failed")

        monkeypatch.setattr(jig_plate_cli.os, "chmod", _boom)
        with pytest.raises(OSError, match="chmod failed"):
            jig_plate_cli.write_atomic(target, b"new")

        assert list(tmp_path.iterdir()) == []

    def test_cleanup_tolerates_a_temp_file_that_is_already_gone(
        self, tmp_path, monkeypatch
    ):
        target = tmp_path / "out.bin"

        def _vanish_then_fail(src, dst):
            jig_plate_cli.os.unlink(src)  # something else removed the temp
            raise OSError("replace failed")

        monkeypatch.setattr(jig_plate_cli.os, "replace", _vanish_then_fail)
        # the original error surfaces, not the FileNotFoundError from
        # the cleanup's own unlink
        with pytest.raises(OSError, match="replace failed") as exc_info:
            jig_plate_cli.write_atomic(target, b"new")
        assert not isinstance(exc_info.value, FileNotFoundError)
        assert list(tmp_path.iterdir()) == []

    def test_file_mode_follows_the_umask_not_0600(self, tmp_path):
        import os

        old = os.umask(0o022)
        try:
            target = tmp_path / "out.bin"
            jig_plate_cli.write_atomic(target, b"x")
        finally:
            os.umask(old)
        assert target.stat().st_mode & 0o777 == 0o644


class TestMain:
    @pytest.fixture
    def _redirected_dirs(self, tmp_path, monkeypatch):
        out_dir = tmp_path / "output"
        img_dir = tmp_path / "images"
        monkeypatch.setattr(jig_plate_cli, "OUT_DIR", out_dir)
        monkeypatch.setattr(jig_plate_cli, "IMG_DIR", img_dir)
        return out_dir, img_dir

    def test_writes_watertight_stamped_stls_and_all_four_diagrams(
        self, _redirected_dirs, monkeypatch
    ):
        out_dir, img_dir = _redirected_dirs
        monkeypatch.setattr(sys, "argv", ["jig-plate.py"])

        jig_plate_cli.main()

        version = jig_plate_cli.VERSION
        plate_path = out_dir / f"jig_plate_{version}.stl"
        coupon_path = out_dir / f"jig_plate_{version}_stack_coupon.stl"
        assert plate_path.exists()
        assert coupon_path.exists()

        expected_header_prefix = f"Jig plate {version}".encode("ascii")
        for path in (plate_path, coupon_path):
            header = path.read_bytes()[:80]
            assert header.startswith(expected_header_prefix)

        import trimesh

        plate = trimesh.load(plate_path)
        coupon = trimesh.load(coupon_path)
        assert plate.is_watertight
        assert coupon.is_watertight

        for name in (
            f"jig_plate_{version}_diagram.png",
            f"jig_plate_{version}_tech_top.png",
            f"jig_plate_{version}_tech_front.png",
            f"jig_plate_{version}_tech_detail.png",
        ):
            assert (img_dir / name).exists()

    def test_console_prints_one_labeled_line_per_mesh(
        self, _redirected_dirs, monkeypatch, capsys
    ):
        monkeypatch.setattr(sys, "argv", ["jig-plate.py"])

        jig_plate_cli.main()

        lines = capsys.readouterr().out.splitlines()
        plate = [ln for ln in lines if ln.startswith("plate ")]
        coupon = [ln for ln in lines if ln.startswith("stack coupon ")]
        assert len(plate) == 1 and len(coupon) == 1
        pattern = (r"^{} +\| watertight: True \| volume cm3: [\d.]+ "
                   r"\| bbox: \[[\d. ]+\] \| faces: \d+$")
        assert re.match(pattern.format("plate"), plate[0]), plate[0]
        assert re.match(pattern.format("stack coupon"), coupon[0]), coupon[0]
        # both prefixes padded to the same width so the columns line up
        assert plate[0].index("|") == coupon[0].index("|")

    def test_custom_label_is_stamped_and_still_watertight(
        self, _redirected_dirs, monkeypatch
    ):
        out_dir, _ = _redirected_dirs
        monkeypatch.setattr(sys, "argv", ["jig-plate.py", "--label", "Card Jig"])

        jig_plate_cli.main()

        import trimesh

        version = jig_plate_cli.VERSION
        plate = trimesh.load(out_dir / f"jig_plate_{version}.stl")
        assert plate.is_watertight

    def test_bad_label_exits_like_an_argparse_error_not_a_traceback(
        self, _redirected_dirs, monkeypatch, capsys
    ):
        monkeypatch.setattr(sys, "argv", ["jig-plate.py", "--label", ""])

        with pytest.raises(SystemExit) as exc_info:
            jig_plate_cli.main()

        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "usage:" in err
        assert re.search(r"label.*empty", err, re.IGNORECASE)

    def test_printer_option_sizes_the_plate_and_stays_watertight(
        self, _redirected_dirs, monkeypatch, capsys
    ):
        out_dir, _ = _redirected_dirs
        monkeypatch.setattr(
            sys, "argv", ["jig-plate.py", "--printer", "x2d-right"])

        jig_plate_cli.main()

        import trimesh

        plate = trimesh.load(
            out_dir / f"jig_plate_{jig_plate_cli.VERSION}.stl")
        assert plate.is_watertight
        assert np.allclose(plate.extents, (225.5, 244.0, 10.5), atol=0.01)
        assert "watertight: True" in capsys.readouterr().out

    def test_unknown_printer_exits_like_an_argparse_error(
        self, _redirected_dirs, monkeypatch, capsys
    ):
        monkeypatch.setattr(sys, "argv", ["jig-plate.py", "--printer", "x9"])

        with pytest.raises(SystemExit) as exc_info:
            jig_plate_cli.main()

        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "usage:" in err
        assert "unknown printer 'x9'" in err

    def test_help_lists_every_printer(self, monkeypatch, capsys):
        from jig_plate_base import printer_names

        monkeypatch.setattr(sys, "argv", ["jig-plate.py", "--help"])
        with pytest.raises(SystemExit):
            jig_plate_cli.main()
        out = " ".join(capsys.readouterr().out.split())
        for name in printer_names():
            assert name in out

    @pytest.mark.parametrize("broken", ["plate", "stack coupon"])
    def test_non_watertight_mesh_still_writes_files_but_exits_nonzero(
        self, _redirected_dirs, monkeypatch, capsys, broken
    ):
        import trimesh

        out_dir, _ = _redirected_dirs
        monkeypatch.setattr(sys, "argv", ["jig-plate.py"])
        real_stamp = jig_plate_cli.stamp
        real_prop = trimesh.Trimesh.is_watertight

        def _break_after_booleans(data, text):
            # the booleans reject a non-watertight input, so flip the
            # property only once the coupon has been built (its stamp is
            # the last step before main() checks both meshes). The plate
            # is the only mesh over 100 cm3; the coupon is ~8 cm3.
            out = real_stamp(data, text)
            if text.startswith("Jig plate") and "stack coupon" in text:
                monkeypatch.setattr(
                    trimesh.Trimesh, "is_watertight",
                    property(lambda self: (
                        False if (self.volume > 100_000) == (broken == "plate")
                        else real_prop.fget(self)
                    )),
                )
            return out

        monkeypatch.setattr(jig_plate_cli, "stamp", _break_after_booleans)

        with pytest.raises(SystemExit) as exc_info:
            jig_plate_cli.main()

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert f"{broken} mesh not watertight" in err
        version = jig_plate_cli.VERSION
        assert (out_dir / f"jig_plate_{version}.stl").exists()
        assert (out_dir / f"jig_plate_{version}_stack_coupon.stl").exists()


class TestMainDoesNotWriteThroughSymlinks:
    def test_symlinked_outputs_are_replaced_and_their_targets_untouched(
        self, tmp_path, monkeypatch
    ):
        out_dir = tmp_path / "output"
        img_dir = tmp_path / "images"
        out_dir.mkdir()
        img_dir.mkdir()
        monkeypatch.setattr(jig_plate_cli, "OUT_DIR", out_dir)
        monkeypatch.setattr(jig_plate_cli, "IMG_DIR", img_dir)
        monkeypatch.setattr(sys, "argv", ["jig-plate.py"])
        version = jig_plate_cli.VERSION
        stl = out_dir / f"jig_plate_{version}.stl"
        png = img_dir / f"jig_plate_{version}_tech_top.png"
        sentinel = tmp_path / "sentinel.txt"
        sentinel.write_bytes(b"do not overwrite me")
        stl.symlink_to(sentinel)
        png.symlink_to(sentinel)

        jig_plate_cli.main()

        assert sentinel.read_bytes() == b"do not overwrite me"
        for path in (stl, png):
            assert path.exists() and not path.is_symlink()
        assert stl.read_bytes()[:80].startswith(f"Jig plate {version}".encode())
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        import trimesh

        assert trimesh.load(stl).is_watertight

    def test_failure_during_main_leaves_no_temp_files(self, tmp_path, monkeypatch):
        out_dir = tmp_path / "output"
        img_dir = tmp_path / "images"
        monkeypatch.setattr(jig_plate_cli, "OUT_DIR", out_dir)
        monkeypatch.setattr(jig_plate_cli, "IMG_DIR", img_dir)
        monkeypatch.setattr(sys, "argv", ["jig-plate.py"])

        def _boom(src, dst):
            raise OSError("disk full")

        monkeypatch.setattr(jig_plate_cli.os, "replace", _boom)
        with pytest.raises(OSError, match="disk full"):
            jig_plate_cli.main()

        assert list(out_dir.iterdir()) == []


class TestRunAsScript:
    def test_dunder_main_guard_calls_main(self, monkeypatch, capsys):
        import runpy

        monkeypatch.setattr(sys, "argv", ["jig-plate.py", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(_SCRIPT), run_name="__main__")
        assert exc_info.value.code == 0
        assert "usage:" in capsys.readouterr().out
