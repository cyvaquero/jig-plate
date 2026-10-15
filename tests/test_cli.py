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

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "jig-plate.py"
_spec = importlib.util.spec_from_file_location("jig_plate_cli", _SCRIPT)
jig_plate_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jig_plate_cli)


class TestStamp:
    def test_pads_a_short_header_to_80_bytes_and_keeps_the_body_intact(self, tmp_path):
        path = tmp_path / "short.stl"
        body = b"body-bytes-that-must-not-move"
        path.write_bytes(b"\x00" * 80 + body)

        jig_plate_cli.stamp(path, "Jig plate 3.0.0")

        data = path.read_bytes()
        assert len(data) == 80 + len(body)
        header = data[:80]
        assert header[: len(b"Jig plate 3.0.0")] == b"Jig plate 3.0.0"
        assert header[len(b"Jig plate 3.0.0") :] == b"\x00" * (
            80 - len(b"Jig plate 3.0.0")
        )
        assert data[80:] == body

    def test_truncates_a_header_over_80_bytes_without_shifting_the_body(self, tmp_path):
        # the 2.4.10 fix: `.encode()[:80]` before `.ljust(80, ...)` --
        # without the [:80] slice, a >= 80 byte string assigned into
        # b[0:80] grows the bytearray instead of truncating, shifting
        # every later byte of the binary STL body and corrupting it.
        path = tmp_path / "long.stl"
        body = b"BODY-MUST-STAY-RIGHT-HERE"
        path.write_bytes(b"\x00" * 80 + body)
        long_header = "x" * 200

        jig_plate_cli.stamp(path, long_header)

        data = path.read_bytes()
        assert len(data) == 80 + len(body), "body shifted -- file corrupted"
        assert data[:80] == b"x" * 80
        assert data[80:] == body


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

    @pytest.mark.parametrize("broken", ["plate", "stack coupon"])
    def test_non_watertight_mesh_still_writes_files_but_exits_nonzero(
        self, _redirected_dirs, monkeypatch, capsys, broken
    ):
        import trimesh

        out_dir, _ = _redirected_dirs
        monkeypatch.setattr(sys, "argv", ["jig-plate.py"])
        real_stamp = jig_plate_cli.stamp
        real_prop = trimesh.Trimesh.is_watertight

        def _break_after_booleans(path, text):
            # the booleans reject a non-watertight input, so flip the
            # property only once the coupon has been built (its stamp is
            # the last step before main() checks both meshes). The plate
            # is the only mesh over 100 cm3; the coupon is ~8 cm3.
            real_stamp(path, text)
            if "stack_coupon" in Path(path).name:
                monkeypatch.setattr(
                    trimesh.Trimesh, "is_watertight",
                    property(lambda self: (
                        False if (self.volume > 100_000) == (broken == "plate")
                        else real_prop.fget(self)
                    )),
                )

        monkeypatch.setattr(jig_plate_cli, "stamp", _break_after_booleans)

        with pytest.raises(SystemExit) as exc_info:
            jig_plate_cli.main()

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert f"{broken} mesh not watertight" in err
        version = jig_plate_cli.VERSION
        assert (out_dir / f"jig_plate_{version}.stl").exists()
        assert (out_dir / f"jig_plate_{version}_stack_coupon.stl").exists()
