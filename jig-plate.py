"""Jig plate -- CLI generator for the stackable laser-jig base plate.

VERSION below is the single source of truth: it drives the output
filenames and the 80-byte binary STL header of both meshes.

This is the base plate only -- no blank-specific pockets. Keeps only what is
blank-agnostic: the magnet bores and the corner stacking rib/groove system.
Pockets for a specific blank are added on top of this base in a separate
script.

The reusable geometry lives in jig_plate_base.py (a hyphenated filename
like this one can't itself be `import`ed). Other generator scripts should
`from jig_plate_base import build_plate` directly rather than running this
CLI; this script is the command-line entry point: argument parsing, STL
export, and the diagrams/technical drawings.

The debossed text label is parameterized via --label (default "Jig Plate");
the logo mark next to it is not. See build_plate()'s `label` parameter.

Issue numbers in the Changelog before 3.1.4 refer to the project's
earlier, non-public tracker, not to this repository's issues.

Changelog
  0.1.0  base design -- magnet bores and corner stacking rib/groove system,
         debossed "Jig Plate" wordmark, no pocket geometry
  1.0.0  first stable release -- script and documentation reviewed, no
         geometry changes; dead code removed from the stacking-joint
         detail drawing; documentation figure/filename inconsistencies
         corrected
  1.0.1  debossed text label parameterized via --label (default unchanged,
         "Jig Plate"); logo mark not parameterized -- a shift in how the
         plate is generated, so iterative bumps now also cover generation
         logic/parameters, not just default-output geometry
  1.0.2  debossed label font pinned to "DejaVu Sans" (matplotlib's bundled
         font) instead of the generic "sans-serif" family alias, so the
         debossed text is identical on macOS, Windows, and Linux instead
         of depending on the host's installed fonts; default output
         unchanged on this machine
  1.1.0  minor release folding 1.0.1-1.0.2
  1.1.1  plate geometry extracted into the importable jig_plate_base.py
         library (build_plate()); this script is now a thin CLI wrapper
         around it -- a shift in how the plate is generated, default
         output unchanged
  2.0.0  major release: two-file architecture becomes the project's public
         structure -- jig_plate_base.build_plate() is the supported API for
         other generator scripts to build on this base plate, jig-plate.py
         is CLI-only. Default output unchanged.
  2.0.1  default back_margin 17 -> 10 mm, matching the already-validated
         front_margin value; moves the back-corner mounting magnet bore
         and stacking rib/groove 3.5 mm closer to the back edge (bore-to-
         edge clearance 5.45 -> 1.95 mm, same clearance the front bore
         already has). Verified no collision with the stacking rib/groove
         (disjoint in X) and still watertight; volume/bbox unchanged.
  2.1.0  minor release folding 2.0.1
  2.1.1  corner stacking rib/groove reinset: stack_inset_x 6 -> 4 mm, and
         a new stack_inset_y (4 mm) decouples the rib/groove Y position
         from bottom_mag_ys, which it previously reused -- now a fixed
         4 mm inset from the corner on both axes, independent of the
         mounting-magnet border bands. Verified no collision with any
         magnet bore (all disjoint footprints) and still watertight;
         volume/bbox unchanged. Edge clearance in X drops 3 -> 1 mm.
  2.1.2  default bottom_mag_inset_x 20 -> 12 mm, bringing the bottom-face
         corner mounting magnets in toward the corner stacking rib/groove
         (the nearer feature -- their Y-bands already overlap, only X
         separated them). Gives a 1.95 mm wall between magnet bore and
         stacking rib/groove, the same clearance value already used
         elsewhere in this design. Verified no collision against any
         magnet bore or stack zone and still watertight; volume/bbox
         unchanged. The stack coupon already fully captures both features
         at this inset -- relabeled to reflect it now also validates this
         wall.
  2.1.3  stack_play now also opens up the groove's length (X), not just
         its width (Y) -- the rib/groove fit previously had zero
         clearance lengthwise while already having 0.2 mm of width play,
         an inconsistency rather than a deliberate tight fit. Groove is
         now 6.2 mm long (rib stays 6.0 mm). Magnet-to-groove wall drops
         1.95 -> 1.85 mm, groove edge clearance 1.0 -> 0.9 mm; both still
         comfortably positive. Verified still watertight; volume/bbox
         unchanged at display precision.
  2.2.0  minor release folding 2.1.1-2.1.3. Corner stacking coupon
         printed and physically test-stacked: fit confirmed good.
  2.2.1  debossed logo/label duplicated on the right face (x=plate_x),
         mirrored to read correctly from +X -- not a plain copy of the
         left-face cut: a viewer at -X (left face) has "right" = -Y,
         but a viewer at +X (right face) has "right" = +Y, so the
         local-x-to-Y mapping is unflipped here versus the left face's
         (verified by rendering each face's cut as its own viewer would
         see it: both read "Jig Plate" correctly, not mirrored/backwards).
         Verified still watertight; volume/bbox unchanged at display
         precision.
  2.3.0  minor release folding 2.2.1. Branding now duplicated on both
         side faces, each mirrored to read correctly from its own side.
  2.3.1  bottom-face honeycomb lightening cutout added to build_plate()
         (new honeycomb_enabled/honeycomb_skin/honeycomb_wall/
         honeycomb_af/honeycomb_margin_x/honeycomb_margin_y params,
         default honeycomb_enabled=True) -- a hex grid of blind pockets
         cut up from the bottom face, sized to match eu-business-card-jig's
         vented pocket floor (23.1 mm across flats, 2.6 mm walls), leaving
         a 2.4 mm top skin. Boundary cells are clipped via boolean
         intersection against the margin field and boolean difference
         against the bottom-corner mounting bores and corner stacking
         rib/groove footprints, rather than dropped whole. Default plate
         volume drops 481.5 -> 282.0 cm3 (-41.4%); top face, all magnet
         bores, and the stacking rib/groove/coupon are untouched. Verified
         still watertight.
  2.3.2  new --honeycomb-af CLI flag exposes build_plate()'s honeycomb_af
         parameter (cell size, mm across flats), default unchanged at
         23.1. Default plate output unaffected; verified still watertight
         at the default and at a sample override (--honeycomb-af 30).
  2.3.3  default honeycomb_af 23.1 -> 22.0 mm (across flats), and the
         --honeycomb-af CLI default follows. Default plate volume
         282.0 -> 285.5 cm3 (-41.4% -> -40.7% vs the solid baseline --
         smaller cells leave proportionally more wall material). Top
         face, all magnet bores, and the stacking rib/groove/coupon are
         untouched. Verified still watertight.
  2.4.0  minor release folding 2.3.1-2.3.3. Bottom-face honeycomb
         lightening cutout (22 mm cells across flats, 2.6 mm walls,
         boundary cells clipped rather than dropped) with cell size
         exposed via --honeycomb-af. Default plate volume
         481.5 -> 285.5 cm3 (-40.7%); top face, all magnet bores, and the
         stacking rib/groove/coupon are untouched. Verified still
         watertight.
  2.4.1  honeycomb_skin default reduced 2.4 -> 1.2 mm (3-perimeter
         minimum shell at a 0.4 mm nozzle) -- the honeycomb pockets
         already cut up to plate_z - honeycomb_skin, so this thins the
         solid top skin they stop at rather than changing what they cut
         up to. Default plate volume 285.5 -> 249.8 cm3 (-48.1% vs the
         solid baseline, up from -40.7%). Top face, all magnet bores, and
         the stacking rib/groove/coupon are untouched. Verified still
         watertight; the top face bridges an unsupported ~19 mm span over
         each honeycomb cell during printing (plate prints bottom-face-
         down per the README) and has not been physically validated for
         sag/warp at this thickness.
  2.4.2  new sparse-coffer bottom-face lightening cutout added to
         build_plate() as an alternative to the honeycomb (new
         coffer_enabled/coffer_skin/coffer_rib/coffer_cols/coffer_rows/
         coffer_margin_x/coffer_margin_y params, default
         coffer_enabled=False -- honeycomb stays the default), plus a new
         --lightening {honeycomb,coffer} CLI flag (default honeycomb) with
         --coffer-rib/--coffer-cols/--coffer-rows to tune it. Coffer is a
         cols x rows grid of large rectangular pockets (4x3 = 12 by
         default, 5 mm ribs) instead of the honeycomb's ~99 cells -- ~8x
         fewer islands to print for essentially the same material removal
         (254.5 cm3 / -47.2% vs the honeycomb's 249.8 cm3 / -48.1%),
         trading distributed bridge spans for fewer, wider ones. Default
         plate output unchanged; verified both paths still watertight.
  2.4.3  new --coffer-skin CLI flag (default 1.2, matching
         build_plate()'s coffer_skin default) for parity with the
         honeycomb path's skin control. Also: --honeycomb-af,
         --coffer-rib, --coffer-cols, --coffer-rows, and --coffer-skin
         now warn to stderr when passed opposite what --lightening
         selects (e.g. --coffer-rib with --lightening honeycomb, the
         default) instead of silently doing nothing -- the build still
         proceeds using only the selected pattern's options. Default
         plate output unaffected; verified still watertight at the
         default, with --coffer-skin overridden, and with each warning
         path triggered.
  2.4.4  new CLI flags expose the rest of build_plate()'s honeycomb
         parameters: --honeycomb-wall, --honeycomb-skin,
         --honeycomb-margin-x, --honeycomb-margin-y. --lightening gains a
         third choice, 'none', for a solid underside, folding in what a
         separately-developed --no-honeycomb flag would have done --
         --lightening is now the single switch across all three patterns
         rather than two overlapping toggles. All new-flag defaults
         unchanged. Also: unit tests added for jig_plate_base.build_plate()
         (32 tests, ~3s, via `pytest`) covering watertightness, volume/bbox
         regression, every honeycomb_*/coffer_* parameter across its
         range, and the CLAUDE.md design constraints. Default plate output
         unaffected; verified still watertight at the default, with
         --lightening none (481.5 cm3, matches the solid baseline), and
         with a combined override of every new flag.
  2.4.5  the honeycomb/coffer bottom-face lightening cutout (2.3.1-2.4.4)
         is scrapped -- material/print-time reduction will be handled in
         the slicer (infill) instead of the model. build_plate() and the
         CLI revert to their pre-2.3.1 state: no honeycomb_*/coffer_*
         parameters, no --lightening/--honeycomb-*/--coffer-* flags.
         Default plate volume 249.8 -> 481.5 cm3 (back to the solid
         slab); top face, all magnet bores, and the stacking
         rib/groove/coupon were already untouched by the removed cutout
         and remain so. Verified still watertight.
  2.4.6  four fixes from independent code review:
         (1) build_plate() now raises ValueError for an empty or
         whitespace-only label instead of crashing deep in matplotlib
         with an unrelated AttributeError.
         (2) the magnet-bore detail drawing no longer hatches 2 mm of air
         in front of the plate's front face -- the material region now
         starts exactly at the face (y=0); the dashed centerline leader
         still extends slightly past it for visual clarity, unchanged.
         (3) the corner stacking groove was 1.6 mm deep, not the
         documented/labeled 1.5 mm -- a stray +0.1 mm overcut at the top
         of the cut (left over from the punch-through-cut pattern used
         elsewhere, not needed for this interior blind pocket) is
         removed. Verified via ray-cast measurement on the mesh, not just
         the cut coordinates. Default plate volume shifts by a
         negligible ~4.2 mm3 (four corners x 0.1 mm x groove footprint);
         unchanged at 481.5 cm3 display precision.
         (4) the magnet-bore-to-stacking-groove wall is 1.85 mm (correct
         since the 2.1.3 groove-play change), but three comments
         (README.md, jig_plate_base.py, jig-plate.py) still said 1.95 mm
         -- corrected to match the actual, verified-on-the-mesh value.
         Historical changelog entries describing 1.95 mm as true *at
         that point in the design's history* are untouched.
         Also: rewrote several tests that could never fail regardless of
         the actual geometry (algebraic self-identities, or comparing a
         field against a formula built from that same object's other
         passthrough fields) into real checks against literal expected
         values and, where the point is to verify a cavity or solid
         region actually exists, `Trimesh.contains()`/ray-cast checks
         against the mesh itself. Fixed the bottom-magnet symmetry and
         stack-position tests, the always-true plate_x<=246 check
         (folded into the bounding-box test, which does check the
         mesh), and the magnet-count symmetry test that would have
         wrongly failed for an odd mag_count_x (parametrized over
         2-5 to prove it now doesn't). New rtree dependency (added to
         requirements.txt) for the ray-cast/contains() tests. Verified
         still watertight; 25/25 tests pass.
  2.4.7  five fixes from a second round of independent code review:
         (1) rtree/pytest were only in requirements.txt, not
         pyproject.toml or the README's requirements list, so a fresh
         `pip install -r requirements.txt` in the project's own .venv
         was the only thing that actually installed them -- 6 of the 25
         tests failed with ModuleNotFoundError otherwise. Added to both.
         (2) test_magnet_bore_to_stack_groove_wall computed the wall
         from PlateGeometry fields (bottom_mag_inset_x, stack_inset_x,
         etc. -- passthroughs of the inputs), so it couldn't catch a bug
         where the real boolean cut diverges from that metadata. Rewrote
         it to ray-cast the actual mesh; verified (by temporarily
         reproducing exactly that kind of divergence) that the old
         version stayed green while the new one correctly fails.
         (3) "front and back bores share X positions" (CLAUDE.md) had no
         test that could actually catch a regression: a contains()-at-
         center probe has ~3 mm of slack from the bore radius, so a 2 mm
         X shift on one side still lands inside the moved cavity. Added
         a test that measures each side's cavity center independently by
         ray-casting and compares them to each other; verified (with the
         same reproduced 2 mm-shift mutation) that it now fails where
         the old contains()-based test didn't.
         (4) the stacking-joint detail drawing had the same hatch-past-
         the-edge bug just fixed in the magnet-bore drawing: det_x0
         (jig-plate.py) came out negative at the default stack_inset_x
         (4 mm), hatching ~3 mm of air past the plate's left edge as
         solid, making the groove-to-plate-edge clearance read as ~4 mm
         instead of 0.9 mm (this window's left boundary -- it doesn't
         reach the magnet-bore-to-groove wall on the right, 1.85 mm,
         fixed separately in 2.4.8). Now clamped to the plate's actual
         [0, plate_x] extent.
         (5) a comment called 1.85 mm "the same clearance value already
         used elsewhere in this design" -- true of the old 1.95 mm
         figure, not of 1.85 mm (grepped the whole design; nothing else
         uses it). Removed the false claim.
         Verified still watertight; 26/26 tests pass.
  2.4.8  fixes from a third round of independent code review:
         (1) build_plate() now validates its inputs instead of crashing
         or silently producing broken/nonsensical geometry: plate_x
         > 246mm (CLAUDE.md's bed/purge-area constraint), mag_count_x
         < 2 (the bore-spacing formula divides by mag_count_x - 1 --
         ZeroDivisionError for exactly 1), mag_depth >= plate_z or
         plate_y/2 (the bottom-corner bore breaks through the top face,
         or the front/back push-fit bores meet/break through the
         opposite face -- reproduced and confirmed both), and a label
         that renders to zero glyphs (e.g. a zero-width character,
         which passes a whitespace check but still crashes deep in
         matplotlib with an unrelated AttributeError -- reproduced and
         confirmed) all now raise a clear ValueError.
         (2) isometric diagram: the "Front edge"/"Left edge" labels and
         the reference magnet markers anchored on the hidden y=0/x=0
         faces, which this view never actually draws (only top,
         x=plate_x, and y=plate_y are rendered) -- their projected
         position could visually coincide with the wrong, actually-
         visible face. Markers moved to the visible back face; labels
         for the undrawn mirror faces removed and folded into the
         visible-face labels ("mirrored on the front/left").
         (3) top-plan view: front/back magnet bores were drawn via
         ax.plot's `ms` (a fixed marker size in points, unrelated to
         the drawing's data scale) instead of a data-space Circle like
         the bottom-face bores correctly use -- rendered far too small,
         inconsistent with the correctly-sized bottom bores at the same
         diameter. Fixed to match.
         (4) stacking-joint detail window ran 2mm past the bottom-corner
         mounting bore's near edge (undrawn in this view), hatching
         part of that cavity as solid; clamped short of it. Added a
         computed (not hardcoded) dimension for the groove-to-plate-edge
         clearance (0.9mm at the defaults), previously undocumented in
         this drawing.
         (5) mesh tests strengthened: groove depth, rib clearance, and
         the magnet-bore-to-groove wall now checked at all four
         corners (previously only the front-left one); new tests
         compare front/back push-fit bore depth and Z-height
         independently on the mesh (previously only X position was
         verified); new test verifies the right-face debossed text
         reads in the correct order (logo before label, matching source
         order) via a 2D mesh scan, not just the sign-convention
         reasoning in a comment.
         Verified still watertight; 38/38 tests pass.
  2.4.9  fixes from a fourth round of independent code review:
         (1) top-plan front/back magnet bores were drawn as circles
         centered on the plate edge -- half the circle rendered outside
         the part. They're blind horizontal bores, not through-holes;
         seen from above a blind bore projects as a mag_d x mag_depth
         rectangle starting at the face and receding inward, so redrawn
         as that (dashed, matching the hidden-feature convention already
         used for the bottom bores). The "through-faces" comment nearby
         was also wrong -- they're blind.
         (2) all five build_plate() validations from 2.4.8 (plate_x,
         mag_count_x, both mag_depth checks, the no-glyph label check)
         had no tests -- deleting any one of them left all 38 tests
         green. Added a parametrized test per check (verified: deleting
         the plate_x>246 check now fails exactly its own test case and
         nothing else).
         (3) many more invalid inputs still silently built a broken
         "watertight" plate instead of failing: mag_d >= plate_z (front/
         back bores break through top/bottom -- reproduced with
         mag_d=10), mag_count_x large enough to merge bores (reproduced
         with mag_count_x=40), plate_x small enough to reverse the
         bore-position order (reproduced with plate_x=50), plate_z too
         thin for the side-face logo (reproduced with plate_z=4),
         stack_h >= plate_z (groove cuts all the way through, reproduced
         with stack_h=9), stack_inset_x/y less than the rib half-width
         (the actual rendered part exceeds 246mm even though plate_x
         itself is 246 -- reproduced with stack_inset_x=2, giving a
         248mm-wide part the old plate_x-only check never saw), and a
         label long enough to run off the side faces (reproduced at 70
         chars). Also: plate_x=nan, a negative plate_x, a float
         mag_count_x, and label=None previously failed with unrelated
         builtin errors instead of a clear message -- now validated
         explicitly. All added as new build_plate() checks with tests.
         (4) labels were parsed as LaTeX mathtext whenever they
         contained a balanced $...$ pair -- "Save $5 and $6" silently
         debossed as "Save 5and6" in italics, and a lone "$\\foo$"
         crashed as invalid mathtext syntax (reproduced both). Text
         rendering now bypasses TextPath's default mathtext
         autodetection entirely (calls the lower-level text-to-path API
         with ismath=False), so every character -- including $ and \\ --
         always renders as its own literal glyph. Separately, a label
         with characters the debossed font has no glyph for (CJK
         scripts, a literal newline) previously produced a visible
         placeholder "tofu" box instead of failing; now checked via the
         font's actual glyph coverage (FreeType) and rejected with the
         offending characters named.
         (5) only the right face had a text-orientation test -- reversing
         the left-face mapping or mirroring the top-face one still left
         all 38 tests green. Added the same 2D-mesh-scan check for the
         left face (expects the opposite Y order from the right face,
         since _add_deboss_left negates the axis) and the top face
         (expects unflipped X order, since _add_deboss doesn't remap
         axes at all).
         Verified still watertight; 65/65 tests pass.
  2.4.10 the "still open" items from the fourth review round:
         (1) PlateGeometry.mag_xs/bottom_mag_ys changed from list to
         tuple -- the dataclass is frozen, but a list field is still
         mutable in place, defeating that; matches stack_xs/stack_ys,
         which were already tuples.
         (2) stamp() now truncates the header to 80 bytes itself before
         padding: `.ljust(80, ...)` alone only pads a *short* string,
         so a header >= 80 bytes was assigned into b[0:80] unchanged,
         which doesn't truncate either -- it grows the bytearray and
         shifts every later byte of the binary STL body, silently
         corrupting the file. Not currently reachable at the default
         label/version lengths, but no longer a landmine.
         (3) both STL headers said the plate is 9mm tall; the actual
         bounding box (with the corner stacking ribs) is 10.5mm -- now
         computed as plate_z + stack_h, not just plate_z.
         (4) a ValueError from build_plate() (e.g. a bad --label) used
         to propagate out of main() as a raw Python traceback; now
         caught and reported the way argparse reports its own errors
         (usage line + message, exit code 2, no traceback). The
         --label help text also named only the top and left faces,
         omitting the right face branding has carried since 2.2.1.
         (5) the stack-coupon comment had its risk backwards (said
         re-check if a feature moves *closer* to the corner, when the
         46x20mm cut region can only lose a feature if an inset grows
         *larger*, moving it away from the corner) and didn't mention
         that the coupon also happens to capture the rightmost front
         push-fit bore at the default mag_xs, not just the bottom
         mounting bore. Both corrected.
         (6) CHANGELOG.md claimed the version appears in the generator
         filename; jig-plate.py's filename never changes, only the
         VERSION constant inside it (mirrored in pyproject.toml) does.
         Corrected to name the actual three places.
         (7) CLAUDE.md said release tags are `x.y.z`; every tag in this
         repo is `vx.y.z`. Also still said the stacking rib/groove is
         positioned off `PLATE_X`/`PLATE_Y` -- stale, pre-dating the
         2.0.0 two-file split; the current lowercase `plate_x`/
         `plate_y` parameters are what the code actually uses.
         (8) drawing fixes (no version-relevant change to the
         generated mesh, bundled into this release alongside the
         fixes above): the isometric diagram's projection was
         mirrored -- iso() reversed the object's own winding, verified
         by the projected top face's signed area coming out negative
         (clockwise) where a right-handed view from above must be
         positive; fixed, and iso_front_face (which only ever drew the
         back, y=plate_y, face) renamed to iso_back_face. The front
         elevation never drew the corner stacking ribs at all -- added,
         since they're visible (not hidden) from that viewing
         direction. Several patches passed alpha= directly to
         matplotlib, which dims the edge by the same amount as the
         fill and made a few section/body outlines nearly invisible at
         the low alpha values used for fills (0.08-0.16) -- fixed by
         baking alpha into the facecolor only, added as a `_faint()`
         helper. "Top face"'s fontweight="semibold" printed a font
         warning on every run (DejaVu Sans has no semibold weight,
         matplotlib silently substitutes bold anyway) -- changed to
         "bold" directly. The stacking-joint detail view now also
         draws the bottom-corner mounting bore itself and the 1.85mm
         wall to it (previously stopped just short of the bore, hiding
         it, and drew that stopping point as if it were a real plate
         edge -- now drawn as a dashed break when it isn't one).
         Verified still watertight; 65/65 tests pass (2 updated for
         the tuple type change).
  2.4.11 fixes from a sixth review round -- the per-parameter validation
         built up over 2.4.8-2.4.10 kept finding new gaps every round
         (mag_inset_x=12 merges a front bore into a bottom one,
         front_margin=0 breaks a bottom bore out the front face,
         stack_play<0 makes the groove narrower than the rib, mag_depth=0
         cuts no bore at all, ...), so build_plate() now checks the
         *derived geometry* directly instead of one bespoke rule per
         parameter: every magnet bore, stacking rib, and groove is built
         as a 3D box, checked for (a) staying within the plate on every
         axis it isn't deliberately anchored to a face on, and (b) not
         colliding with any other feature's box. Reproduced and confirmed
         every case above, plus everything the five checks it replaces
         already covered (mag_depth/mag_d/stack_h breaking through a
         face, bores merging from too many/too-close bores, the rib/
         groove breaching an edge) -- one mechanism now covers all of
         them, independent of which parameter combination causes it.
         Bounding boxes around the round bores are a conservative
         (not exact) approximation, noted in the code. Kept as separate,
         still-bespoke checks: type/finite/sign validation, mag_count_x
         >= 2 (divide-by-zero, not a geometry question), stack_play >= 0
         (rib/groove size compatibility for stacking, not a same-plate
         collision), plate_x <= 246mm (CLAUDE.md's bed/purge constraint),
         and the label/branding-footprint checks (2D face fit, a
         different category from 3D mechanical collision).
         Also: the validation tests were weaker than claimed -- deleting
         any one of five checks left the suite green, because every case
         used a bare pytest.raises(ValueError) that passes no matter
         which check fires. Every case now matches the specific message
         (verified: deleting a check now fails only the case naming it,
         checked for both a single check and the whole collision
         mechanism). The top-face text-orientation test only caught the
         logo and label swapping order as whole blocks, not the letters
         within the label itself being reversed -- added a test using an
         asymmetric two-letter label ("IW", narrow-then-wide) that sub-
         splits the text region and checks the letters' own order;
         verified it fails where the block-level check doesn't, by
         temporarily reversing the rendered character order.
         Drawing fixes (bundled into this same release since it also
         contains the changes above -- see CLAUDE.md's versioning rules
         for why a drawing-only change alone wouldn't bump anything):
         every "Scale N:1" label across all four drawings is deleted --
         S is a coordinate multiplier that cancels out under equal-
         aspect autoscaling, so the labeled scale was never the actual
         one (measured: labeled 2:1/10:1/45:1/22:1, actual around
         0.74:1/1.2:1/5:1/5:1) -- a screen render doesn't have a
         meaningful physical scale to state, and the dimension figures
         on each drawing are what's accurate regardless. The _faint()
         edge-dimming fix from 5892a23 had only been applied to 3 of 8
         affected patches; applied to the remaining 5 (isometric magnet/
         rib markers, top-plan rib, magnet-bore-detail's reference
         magnet box, stacking-joint's rib). The magnet-bore-detail panel
         had the same two bugs the stacking-joint panel was fixed for in
         5892a23 but never got the fix itself: its own window cutoff
         (11.2mm) was drawn as a real edge (now a dashed break, matching
         the real front/back-face edge staying solid), and a redundant
         face-outline line overshot the part's actual Z extent by 1mm on
         each end (removed, superseded by the new edge lines drawn at
         the true bounds).
         Verified still watertight; 80/80 tests pass.
  2.4.12 the two items a seventh review round flagged as the ones that
         matter, both closed by extending the derived-geometry check
         from 2.4.11 rather than adding more bespoke rules:
         (1) the debossed branding (top-face logo/label, and its mirrored
         copies on the left/right faces) was never a feature box in that
         check, so deboss_d had no upper limit and a long label at a
         shallow deboss_d could reach into a magnet bore without being
         rejected. Reproduced (deboss_d=9, deboss_d=20, and a 30-"W" label
         at deboss_d=2, all previously accepted) and fixed by computing
         each branding footprint once, early in build_plate(), and adding
         it to the same feature-box list the mechanical bores/rib/groove
         already use -- top-face box anchored to z_max, left/right-face
         boxes anchored to x_min/x_max respectively. All three cases now
         raise.
         (2) both containment and pairwise-collision checks accepted any
         positive separation (1e-6 epsilon), so a wall could be print-
         impossible without being invalid. Reproduced three cases the
         check let through: bottom_mag_inset_x=10.16 (0.01mm bore-to-
         groove wall), front_margin=6.102 (0.001mm bottom-bore-to-front-
         face wall), mag_depth=8.99 (0.01mm skin over the bottom bores).
         Fixed with a real _min_wall = 0.8mm (two 0.4mm-nozzle perimeters)
         applied to every non-anchored boundary and every pairwise gap;
         the 1e-6 epsilon is now reserved for boundaries deliberately
         anchored flush to a face (a bore's mouth, a branding cut's
         depth). Verified via mutation testing: weakening _min_wall back
         to 1e-6 fails exactly the 5 tests that depend on it and no
         others (at 3.0.0, after 2.4.13's deeper groove, it fails 4).
         Also fixes bundled from the same round (all documentation/
         drawing, no geometry change):
         (3) the magnet-bore-detail panel's front face (y=0) had no
         outline above or below the bore -- a leftover comment claimed it
         was "drawn solid" but no line was ever added for it when the
         other three edges were split out in 2.4.11; restored.
         (4) jig_plate_base.py's build_plate() docstring pointed at
         CHANGELOG.md for current defaults, but that file only covers
         released 2.x minors and its latest entry describes the honeycomb
         cutout removed on develop in 2.4.5 -- repointed at this file's
         own Changelog block, which stays current every round.
         CHANGELOG.md gets a note to the same effect. README.md: the
         magnet-polarity paragraph and the "mate either way round"
         feature bullet described what sounded like the same guarantee
         but weren't -- bore *positions* are symmetric so plates still
         line up geometrically when turned 180 degrees, but a fixed
         front/back polarity convention only attracts an unrotated
         neighbor; reworded both to say so explicitly rather than
         changing the (still undecided) physical polarity design. The
         test-coupon bullet left out that the coupon also carries the
         rightmost front push-fit bore at default mag_xs, which is what
         lets it validate the bore-to-groove wall; added.
         (5) the top plan view drew the stacking rib but never the
         groove; added as a dashed rectangle (hidden-line convention)
         around each rib, sized from stack_len/stack_w + stack_play like
         the mechanical geometry itself. The stacking-joint detail sheet
         gained a caption noting it's a composite view (groove and bore
         cuts shown at their own Y positions, not one cross-section
         plane) rather than trying to draw a single plane that doesn't
         exist in the real geometry.
         (6) re-verified the prior round's housekeeping claims (stale
         origin/feature/sparse-coffer-lightening branch, stale output/
         images files): both already false by the time this round
         started -- no such remote branch exists, and output/images hold
         only current-version files. No action needed.
         Verified still watertight; 86/86 tests pass.
  2.4.13 stack_play now also opens up the groove's depth (Z), not just
         its length and width (X/Y, since 2.1.3) -- the groove was cut
         exactly stack_h deep, the same height as the rib, so the rib
         would bottom out in the groove with zero *deliberate* vertical
         clearance even though X/Y already had 0.2mm of play. Groove
         depth is now stack_h + stack_play; the rib itself is unchanged.
         Framed against the actual mesh, not the documented figure: the
         groove measured 1.6mm deep pre-2.4.6 (a stray +0.1mm overcut,
         itself a bug, not deliberate clearance), 1.5mm from 2.4.6-2.4.12
         (the overcut fixed, leaving true zero clearance), and is 1.7mm
         now -- net +0.1mm versus the pre-2.4.6/2.4.0 mesh, and the first
         time this clearance has been a deliberate design choice rather
         than either a bug or its absence. Because a deeper groove can
         only ever make the rib seat *more* easily (never obstruct it,
         since nothing sits below the rib to block it going in further),
         and the floor still leaves 481.5cm3 - a fraction of a cm3 of
         material above the groove at every corner, this is a safe
         direction to move even without a fresh print/stack test of this
         exact depth. stack_play splits in half per side across X/Y (the
         rib can land off-center in the groove either way) but applies
         in full to Z (the groove has only one closed side, its floor,
         for the rib to bottom out against) -- documented in
         build_plate()'s and this groove-feature check's own comments,
         not just implied by the code.
         Also updated to match: the stacking-joint detail drawing's
         groove depth and "deep" dimension label, and the stack_play<0
         error message (now "narrower and shallower" instead of just
         "narrower"). Default plate volume 481.483 -> 481.475 cm3 (the
         four corners' grooves each remove a negligible extra
         ~0.2mm x groove footprint of material); top face, all magnet
         bores, and the rib/coupon footprint are otherwise untouched.
         Verified still watertight; 86/86 tests pass, including a new
         ray-cast check of the actual groove depth (renamed from
         test_stacking_groove_depth_matches_stack_h) -- verified via
         mutation testing that reverting the Z depth to plain stack_h
         fails exactly that test plus the volume regression test, no
         others.
  3.0.0  major release folding 2.4.1-2.4.13. See CHANGELOG.md for the
         full record; in short: the bottom-face honeycomb/coffer
         lightening cutout 2.4.0 shipped with was built out further
         (2.4.1-2.4.4) and then fully reverted (2.4.5) -- material/
         print-time reduction is handled in the slicer instead, so the
         default plate is a solid slab again, unchanged from 2.3.0/
         pre-2.3.1. Everything else is the independent code-review
         rounds of 2.4.6-2.4.12 plus the 2.4.13 groove-depth fix:
         build_plate() went from no input validation to a
         derived-geometry check covering every
         mechanical feature and the debossed branding, with a real
         0.8mm minimum wall and full X/Y/Z rib-groove fit play; several
         drawing and STL-header bugs were fixed; the test suite grew
         from 0 to 86 tests, many of them mutation-tested as each entry
         above notes (not all: see 3.0.3 and 3.0.6).
  3.0.1  process/docs only, no geometry change: every merged branch bumps
         the iterative version and gets a CHANGELOG.md entry (previously
         model changes only / releases only); git-flow branches+PRs and
         the no-reply commit identity; CLAUDE.md is cut to what is
         repo-specific (under 120 lines) and gains an American English
         convention (#26 tracks the leftover British spellings), a
         verified-output-formats section, the X.Y.0 bump at the release
         merge into main, bare release tags (no `v` from 3.0.1 on),
         manual issue closing for PRs into develop, and the
         blind-review accessibility scope.
         Verified: plate and coupon STL triangle data (bytes 80+)
         byte-identical to 3.0.0; both meshes watertight; full test
         suite passes.
  3.0.3  test only, no geometry change: the dollar-sign label test asserts on
         the glyph polygons from _text_polys instead of just watertightness,
         so re-enabling mathtext (ismath=True) now fails it (#1).
         Verified: with ismath=True the test fails, reverted it passes;
         plate and coupon STL triangle data (bytes 80+) byte-identical to
         3.0.1; both meshes watertight; full suite passes.
  3.0.4  build_plate() rejects unprintable feature sizes (no default change):
         mag_d, mag_depth, stack_w, stack_len, stack_h >= 0.8 mm (the new
         module-level _MIN_WALL), deboss_d >= 0.2 mm, stack_play >= 0.1 mm;
         the old checks only required > 0 (stack_play >= 0), so e.g.
         stack_h=0.05 built a plate with no usable rib (#6).
         Verified: each repro raises ValueError naming the parameter,
         exact minimums build; plate and coupon STL triangle data (bytes
         80+) byte-identical to 3.0.1; both meshes watertight; full suite
         passes.
  3.0.5  packaging/docs only, no geometry change: requirements.lock (pip-compile
         --generate-hashes from requirements.txt) pins and hashes every
         dependency; README and CLAUDE.md setup install from it on Python
         3.14 (#16).
         Verified: a fresh venv from the lock (--require-hashes) builds
         plate and coupon STLs byte-identical (bytes 80+) to the previous
         venv's, both meshes watertight, full suite passes.
  3.0.6  review notes from 3.0.0 (#28), no geometry change: main() still
         writes both STLs but exits 1 with an error on stderr when a mesh
         is not watertight; the top plan draws the debossed branding
         footprint (new PlateGeometry.top_branding_bounds); the isometric
         diagram notes its x3 vertical exaggeration and its labels clear
         the part; the front elevation shows the hidden bottom bores and
         grooves dashed; the 0.2 mm clearance dimension puts its arrowheads outside;
         the detail sheet's magnet size comes from constants; stamp() uses
         Path I/O; pytest and rtree move to a test extra in pyproject.toml;
         new tests pin the default mag_xs and the side-face branding
         collision box.
         Verified: plate and coupon STL triangle data (bytes 80+)
         byte-identical to 3.0.5; both meshes watertight; PNGs inspected
         before and after; each new test fails when its fix is reverted;
         full suite passes.
  3.0.7  docs only: CLAUDE.md drops its restatement of the bare x.y.z
         tag format (it contradicted x.y.z.h hotfix tags) and defers to
         the global rules; the note that tags through v3.0.0 keep their
         `v` prefix stays. Verified: plate and coupon STL triangle data
         (bytes 80+) byte-identical to 3.0.6; both meshes watertight;
         full test suite passes.
  3.0.8  packaging only, no geometry change: pyproject.toml gains a
         [build-system] table (setuptools>=61, the first release with
         PEP 621 support) and [tool.setuptools] py-modules =
         ["jig_plate_base"], so `pip install .`, `pip install -e .` and
         `.[test]` work on the flat layout even with output/ and images/
         present; they previously failed with "Multiple top-level packages
         discovered". Verified in a fresh 3.14 venv: all three installs
         succeed and `import jig_plate_base` works from outside the repo;
         STLs (bytes 80+) byte-identical to 3.0.7; both meshes watertight;
         full test suite passes.
  3.0.9  drawing fix, no geometry change (#36): the isometric diagram's
         "Back edge" leader is now anchored left of the "Magnet bore"
         bore (x fraction 0.25 -> 0.45), so it runs under that leader
         and the two no longer cross.
         New tests/test_diagram.py computes the leader segments from the
         figure's artists and asserts no two intersect.
         Verified: plate and coupon STL triangle data (bytes 80+)
         byte-identical to 3.0.7; both meshes watertight; diagram PNG
         inspected (no crossings, no label overlaps); full suite passes;
         the new test fails with the old label position.
  3.0.10 drawing fix, no geometry change (#37): the isometric diagram's
         6 x 1.5 mm corner stacking rib was a few pixels under the
         leader's dot. A dashed frame now marks it (the dot sits on the
         frame), and a "Detail A, x6" inset redraws the corner at six
         times the diagram's scale, labeled with its zoom and the rib's
         size, in the empty area above the plate; its rib faces are
         opaque so they hide the corner edges behind them. New
         tests/test_diagram_inset.py pins the label, the true rendered
         magnification, that the inset clears the plate and labels, and
         that the rib faces are opaque.
         Verified: plate and coupon STL triangle data (bytes 80+)
         byte-identical to 3.0.7; both meshes watertight; diagram PNG
         inspected; full suite passes; the tests fail when the zoom or
         placement is broken.
  3.0.11 docs only, no geometry or drawing change: the README embeds
         the four drawings, copied to docs/images/ (unversioned names)
         with dimensioned alt text. Verified: STL triangle data (bytes
         80+) byte-identical to 3.0.10; both meshes watertight; full
         test suite passes; drawings viewed.
  3.0.12 docs only (#22): the 3.0.0 notes (here and in CHANGELOG.md) no
         longer claim every test was mutation-tested -- many were, and
         3.0.3/3.0.6 closed the gaps later review found; the review
         rounds are 2.4.6-2.4.12 (2.4.13 was a follow-up fix, and the
         first 32 tests predate them, at 2.4.4); the 2.4.12 entry's
         "exactly the 5 tests" now notes the same mutation fails 4 at
         3.0.0. Verified by rerunning that mutation at both commits
         (5 failed at 2.4.12, 4 at 3.0.0); STL triangle data (bytes
         80+) byte-identical to 3.0.11; both meshes watertight; full
         test suite passes.
  3.0.13 docs only (#23): CHANGELOG.md's 3.0.0 section now lists the
         changes that can break a 2.4.0 caller -- PlateGeometry's
         honeycomb_* fields removed, mag_xs/bottom_mag_ys now tuples,
         a rejected --label exiting 2 with a usage message instead of
         a traceback. Each checked against `git diff v2.4.0 v3.0.0`.
         Verified: STL triangle data (bytes 80+) byte-identical to
         3.0.11; both meshes watertight; full test suite passes.
  3.0.14 spelling only (#26): American English in comments, docstrings
         (including this Changelog block), test comments, test
         identifiers and the README: centre/centred/centreline, labelled
         and neighbour(s) become center/centered/centerline, labeled and
         neighbor(s). None of
         them was rendered into a drawing. CHANGELOG.md's historical
         entries keep their wording. Verified: STL triangle data (bytes
         80+) byte-identical to 3.0.11; both meshes watertight; full
         test suite passes.
  3.0.15 test docstring only (#30): TestParameterValidation no longer
         says CHANGELOG.md records only major/minor releases; it has
         an entry for every iterative change from 3.0.1 on. Verified:
         STL triangle data (bytes 80+) byte-identical to 3.0.11; both
         meshes watertight; full test suite passes.
  3.0.16 build_plate(side_branding=True) (#7): library-only switch; False
         omits the left/right-face deboss and its Z-fit check and
         keep-out boxes, so plates thinner than about 7.4 mm (which the
         fixed 4 mm side text rejected) can be built. Top-face branding
         is unchanged; non-bool values raise ValueError. The CLI is
         unchanged. Verified: STL triangle data (bytes 80+) byte-identical
         to 3.0.11 at the default; both meshes watertight; plate_z=7 with
         side_branding=False builds watertight and still raises without
         it; new tests pass and fail under mutation.
  3.0.17 tests only (#48): the four text-orientation tests bound their
         contains() probe grid by the mesh's own deboss-floor vertices
         (padded 1 mm) instead of scanning the whole face; suite 13-14 s
         -> about 6 s. Verified: mirroring each face's deboss (parity kept,
         so the mesh stays a volume) fails only that face's test(s);
         STL triangle data (bytes 80+) byte-identical to 3.0.11; both
         meshes watertight; full test suite passes.
  3.0.18 drawing label contrast (#50): the "61.5 typ.", "magnet 6x3" and
         "rib (top face)" labels were 2.87-3.57:1; they now use DIM_COLOR and
         the new VIOLET_TEXT / AMBER_TEXT (lines and fills keep VIOLET and
         AMBER), all >= 4.5:1. Verified: STL triangle data (bytes 80+)
         byte-identical to 3.0.11; both meshes watertight; new test fails
         on the old colors; drawings viewed; full test suite passes.
  3.0.19 drawing feature keys (#51): the top plan and front elevation each
         carry a key naming the stacking groove, the mounting and edge
         magnet bores and the rib, with each swatch in the line style the
         feature is drawn in (add_key gained a points-based mode); hidden
         magnet bores are dotted and hidden grooves dashed on both sheets. Verified:
         STL triangle data (bytes 80+) byte-identical to 3.0.11; both
         meshes watertight; new tests fail without the key or with a
         wrong swatch style; drawings viewed; full test suite passes.
  3.0.20 label length precheck (#52): build_plate measures the label with
         a linear text-width call before rendering glyphs and rejects one
         whose inked span (leading/trailing no-outline characters such as
         spaces ignored) is wider than plate_x at once (label "W"*6000:
         5.5 s -> 0.14 s); the exact checks stay. Verified: STL triangle data (bytes 80+)
         byte-identical to 3.0.11; both meshes watertight; the longest
         buildable "W" run (44) still builds; new tests fail under
         mutation; full test suite passes.
  3.0.21 low review notes of #54: the label is checked against plate_y
         only with side_branding; non-finite or overflowing numbers
         (10**400) raise ValueError naming the parameter; mag_inset_x and
         stack_inset_x >= plate_x / 2 are rejected; drawings: every label
         >= 7 pt, narrower front elevation (its 4.5 dimension moved
         outside the plate), outside arrows on the 4 mm rib-inset
         dimension, outlined key swatches, opaque violet
         extension lines, feature keys anchored to the axes so the
         shorter front elevation doesn't crop its key (new test: no
         drawing has ink at its PNG edge); README images link to their
         files and the
         Dimensions table has headers; the CLI prints one labeled line per
         mesh. Verified: STL triangle data (bytes 80+) byte-identical to
         3.0.11; both meshes watertight; drawings viewed; every new test
         fails on 3.0.17 and passes now; full test suite passes.
  3.0.22 docs only: CLAUDE.md refreshes docs/images at every release
         bump as well as on a drawing change, and counts the drawing code
         and CLI output as reader-facing text for the accessibility
         reviewer. Verified: STL triangle data (bytes 80+) byte-identical
         to 3.0.11; both meshes watertight; full test suite passes.
  3.0.23 the CLI no longer writes through a symlink at an output path: each
         STL and PNG is built in memory and written to a temp file in the
         target's directory, then os.replace()d onto it, so a symlink is
         replaced instead of followed and a failed write leaves no partial
         file. stamp() now takes and returns bytes. Verified: STL triangle
         data (bytes 80+) byte-identical to 3.0.11; both meshes watertight;
         PNGs byte-identical to 3.0.22 renders; full test suite passes.
  3.0.24 build_plate() accepts numpy scalars (np.float32, np.int64) and any
         numbers.Real/Integral for its parameters, still rejecting bool and
         np.bool_; values reach the geometry as plain Python numbers.
         Verified: STL triangle data (bytes 80+) byte-identical to 3.0.11;
         np.float32/np.int64 build is byte-identical to the defaults; both
         meshes watertight; full test suite passes.
  3.0.25 docs only: the CHANGELOG summary table has a real header row
         (Item, Value) instead of an empty one. Verified: STL triangle
         data (bytes 80+) byte-identical to 3.0.11; both meshes
         watertight; full test suite passes.
  3.0.26 docs only (#54): README and build_plate docstring say the
         default bores need plate_z of about 7.7 mm, so side_branding=False
         alone doesn't allow a thinner plate. Verified: plate_z=7.6 raises
         and 7.7 builds at default bores; STL triangle data (bytes 80+)
         byte-identical to 3.0.11; both meshes watertight; full test suite
         passes.
  3.0.27 docs only (#54): README and build_plate docstring give the side
         mark's real height (4 mm label plus logo, 5.76 mm at the default
         label, measured from the left-face deboss vertices) instead of
         "4 mm tall". Verified: STL triangle data (bytes 80+) byte-identical
         to 3.0.11; both meshes watertight; full test suite passes.
  3.1.0  minor release: folds 3.0.1-3.0.27 (side_branding switch, numpy
         scalar parameters, labeled CLI lines, atomic output writes, the
         early label-length check, accessible drawings with feature keys,
         README drawings). Verified: STL triangle data (bytes 80+)
         byte-identical to 3.0.0 and 3.0.11; both meshes watertight;
         full test suite passes (199); drawings viewed.
  3.1.1  tests only (#68): six new tests (205 in all) cover label-cutter
         and write_atomic paths no test reached: the buffer(0) repair of
         an invalid glyph polygon, the empty/tiny-piece skip in the three
         deboss cutters, write_atomic's cleanup when the temp file is
         already gone, and the __main__ guard. Each was mutation-checked
         (breaking the line fails its test). Verified: STL triangle data
         (bytes 80+) byte-identical to 3.1.0; both meshes watertight; full
         test suite passes (205).
  3.1.2  pruned two unreachable fit-check branches (#68): the skip of a
         feature with no bounds (every feature has bounds) and the "extends
         below the bottom face" error for a stacking rib (the bore checks,
         listed first, already need plate_z >= mag_depth + 0.8 >= 1.6, so a
         thinner plate fails on a bore first). One new test (206 in all)
         pins that invariant. Verified: sweeping plate_z, mag_depth and
         other parameters through an instrumented copy never reached either
         branch; error messages for a set of invalid inputs identical to
         3.1.1; STL triangle data (bytes 80+) byte-identical to 3.1.1; both
         meshes watertight; full test suite passes (206).
  3.1.3  MIT license (#29): adds LICENSE and replaces the README's "no
         license" line. No code change. Verified: STL triangle data
         (bytes 80+) byte-identical to 3.1.2; both meshes watertight; full
         test suite passes (206).
  3.1.4  per-printer profiles (#2): build_plate(printer=...) and a new
         --printer CLI option select a Bambu Lab print area (a1, p1s, p2s,
         x1c, h2s, h3c, and a left/right profile for each of x2d, h2d,
         h2c; a bare dual-nozzle name means the larger nozzle). A printer
         sets the default plate size (largest keep-out-clear rectangle
         less 10 mm per axis) and plate_x, plate_y and the full height
         are checked against it, naming printer and axis. No printer
         keeps the 246 x 218 default and the 246 mm X cap. The printer
         figures are from search-result quotes and still need a check
         against Bambu Lab's official spec pages. Verified: STL triangle
         data (bytes 80+) byte-identical to 3.1.3 with no --printer; both
         meshes watertight for every profile; full test suite passes.
  3.1.5  isometric diagram legend spacing (#4): the plate / magnets /
         stacking rib key was laid out in data units, so at the smaller
         scale a larger printer plate gets, its entries crowded and
         "magnets" ran into the next swatch. The key is now laid out in
         points from the bottom of the axes, with swatch size, gaps and
         label widths fixed, so it reads the same at every plate size;
         the "Vertical scale" note moved to sit under it. Verified: STL
         triangle data (bytes 80+) byte-identical to 3.1.4 with no
         --printer; both meshes watertight; diagrams viewed for the
         default, h2s, x2d-right and a1; new tests fail on the old key;
         full test suite passes.
  3.1.6  printer name in output names (#5): with --printer, the canonical
         profile name (aliases resolved: h2d gives h2d-left) is added to
         every file name, as jig_plate_<VERSION>_<printer>.stl,
         _<printer>_stack_coupon.stl and _<printer>_diagram.png (and the
         three tech sheets), and to both STL headers ("Jig plate 3.1.6 |
         h2s | 330x308x10.5mm | ..."), so builds for different printers no
         longer overwrite each other. The coupon header drops "corner, "
         with a printer so the longest name still fits 80 bytes. No
         printer: names and headers unchanged. Verified: STL triangle data
         (bytes 80+) byte-identical to 3.1.5 with no --printer, and the
         no-printer header differs only in the version; both meshes
         watertight; two printers' builds coexist; new tests fail without
         the stem, the header tag or alias resolution; full test suite
         passes.
  3.1.7  docs only (#11): this docstring and CHANGELOG.md say that issue
         numbers before 3.1.4 refer to the project's earlier, non-public
         tracker. Verified: STL triangle data (bytes 80+) byte-identical
         to 3.1.6; both meshes watertight; full test suite passes.
"""
import argparse
import io
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import to_rgba as _to_rgba
from matplotlib.transforms import Affine2D, ScaledTranslation

from jig_plate_base import build_plate, bx, get_printer_profile, printer_names


def _faint(color, alpha):
    """RGBA facecolor with `alpha` baked in -- NOT the same as passing
    alpha= to a Patch constructor, which dims the edge by the same
    amount and made several section/body outlines nearly invisible."""
    return _to_rgba(color, alpha)


def _solid(color, alpha):
    """Opaque facecolor: `color` mixed with the background at `alpha`. Use
    it where a face must hide the lines behind it, which _faint's
    see-through fill doesn't."""
    fg, bg = _to_rgba(color), _to_rgba(BG)
    return tuple(alpha * c + (1 - alpha) * b for c, b in zip(fg[:3], bg[:3])) + (1.0,)

VERSION = "3.1.7"
OUT_DIR = Path(__file__).resolve().parent / "output"
IMG_DIR = Path(__file__).resolve().parent / "images"

# Z exaggeration of the isometric overview (the plate is only 9 mm thick)
ISO_Z_EXAGGERATION = 3
# the push-fit magnet the detail sheet draws in the bore: a 6 mm x 3 mm
# disc (the bore itself is geom.mag_d x geom.mag_depth, slightly larger)
MAGNET_D = 6.0
MAGNET_LEN = 3.0


def write_atomic(path, data):
    """Write `data` (bytes) to `path` via a temp file and os.replace().

    The temp file sits in the target's directory so the replace stays on
    one filesystem. os.replace() swaps the directory entry, so a symlink
    already at `path` is replaced, not followed: the file it points to is
    never touched. The temp file is removed if anything fails.
    """
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        # mkstemp makes the file 0600; match what open() would have given
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(tmp, 0o666 & ~umask)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _export_stl(mesh, path, text):
    """Export `mesh` as binary STL with the version header, written once."""
    write_atomic(path, stamp(mesh.export(file_type="stl"), text))


def _save_png(fig, path, **kwargs):
    """Render `fig` to PNG in memory and write it with write_atomic()."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", **kwargs)
    write_atomic(path, buf.getvalue())


# stamp the 80-byte binary STL header so the version travels with the file
def stamp(data, text):
    # explicitly truncated to 80 bytes before the pad: `.ljust(80, ...)`
    # alone only pads a *short* string -- for one already >= 80 bytes it
    # returns it unchanged, and assigning that into b[0:80] doesn't
    # truncate either, it grows the bytearray and shifts every byte of
    # the binary STL body after it, silently corrupting the file.
    header = text.encode("ascii")[:80].ljust(80, b"\x00")
    b = bytearray(data)
    b[0:80] = header
    return bytes(b)


# -------- diagram / technical drawing styling --------
AMBER = "#BA7517"
VIOLET = "#7F77DD"
# darker variants for small text: VIOLET and AMBER are for lines and fills
# only (3:1 non-text contrast); text needs 4.5:1 on BG or on the tinted fill
VIOLET_TEXT = "#4f46b8"
AMBER_TEXT = "#7a4a0e"
SHAPE = "#888780"
FG = "#1a1915"
MUTED = "#6b6860"
BG = "#faf9f7"

# smallest label or annotation size on any drawing, in points (about 6 px
# tall at the README's display width is too small to read; 7 pt is the floor)
MIN_LABEL_PT = 7

C30, S30 = np.cos(np.radians(30)), np.sin(np.radians(30))


def iso(x, y, z):
    # (y - x), not (x - y): the object's own right-handed boundary (top
    # face traversed 0,0 -> +x,0 -> +x,+y -> 0,+y, the standard CCW
    # winding for a face whose outward normal is +Z) must still project
    # as CCW to a viewer above the object, or the whole scene is a
    # mirror image of the real part -- verified with (x - y) by shoelace
    # area on the projected top face: it came out negative (CW).
    return (C30 * (y - x), -S30 * (x + y) + z)


def iso_rect(x0, y0, x1, y1, z):
    return [iso(x0, y0, z), iso(x1, y0, z), iso(x1, y1, z), iso(x0, y1, z)]


def iso_right_face(x, y0, y1, z0, z1):
    return [iso(x, y0, z0), iso(x, y1, z0), iso(x, y1, z1), iso(x, y0, z1)]


def iso_back_face(x0, x1, y, z0, z1):
    return [iso(x0, y, z0), iso(x1, y, z0), iso(x1, y, z1), iso(x0, y, z1)]


def leader(ax, anchor, text_pos, label, ha="left", dashed=True):
    ax.plot(*anchor, "o", color=FG, ms=3.5, zorder=5)
    ax.plot([anchor[0], text_pos[0]], [anchor[1], text_pos[1]],
            color=MUTED, lw=0.8,
            ls=(0, (3, 2)) if dashed else "-", zorder=4)
    ax.text(text_pos[0], text_pos[1], label, fontsize=8.5,
            fontfamily="sans-serif", color=FG, ha=ha, va="center",
            zorder=6)


def add_key(ax, items, y_pos=None, below_pt=None):
    """Draw a key of (label, color) swatches.

    Default: one centered row of color swatches, as on the isometric
    overview. It is laid out in points from the axes' bottom edge (`y_pos`
    is the row's center height above it, default ROW_KEY_Y_PT), so spacing,
    swatch and text size do not change with the drawing's data scale.

    With below_pt: a column of feature entries under the axes, laid out in
    points so it reads the same whatever the drawing's scale. Each item is
    (label, color, style) where style gives the swatch outline: `shape`
    ("rect" or "circle"), `ls` (line style, drawn as the feature is drawn,
    so the key does not rely on color) and `fc` (fill or "none"). Call it
    after the view is final: it positions the key from the axes box.
    """
    if below_pt is not None:
        _add_point_key(ax, items, below_pt)
        return
    fig = ax.figure
    ax.apply_aspect()
    renderer = fig.canvas.get_renderer()
    y = ROW_KEY_Y_PT if y_pos is None else y_pos
    # points, origin at the axes' bottom-center; the origin is looked up
    # through transAxes at draw time, so the row moves with the axes when
    # bbox_inches="tight" shifts the figure
    to_px = (Affine2D().scale(1 / 72) + fig.dpi_scale_trans
             + ScaledTranslation(0.5, 0, ax.transAxes))
    entries = []
    for label, color, *_ in items:
        # alpha baked into the fill only; the MUTED outline stays opaque so
        # the swatch edge reaches 3:1 against BG
        patch = FancyBboxPatch((0, y - ROW_KEY_SWATCH_PT / 2),
                               ROW_KEY_SWATCH_PT, ROW_KEY_SWATCH_PT,
                               boxstyle="round,pad=1", fc=_faint(color, 0.7),
                               ec=MUTED, lw=0.6, zorder=5, transform=to_px,
                               clip_on=False)
        text = ax.text(0, y, label, fontsize=7.5, color=MUTED, va="center",
                       ha="left", fontfamily="sans-serif", zorder=5,
                       transform=to_px)
        ax.add_patch(patch)
        w_pt = text.get_window_extent(renderer).width * 72 / fig.dpi
        entries.append((patch, text, w_pt))
    # swatch + gap + label, with a fixed gap between entries
    widths = [ROW_KEY_SWATCH_PT + 2 + ROW_KEY_TEXT_GAP_PT + w
              for *_, w in entries]
    x = -(sum(widths) + ROW_KEY_ENTRY_GAP_PT * (len(widths) - 1)) / 2
    for (patch, text, _), w in zip(entries, widths):
        patch.set_x(x + 1)
        text.set_position((x + 2 + ROW_KEY_SWATCH_PT + ROW_KEY_TEXT_GAP_PT, y))
        x += w + ROW_KEY_ENTRY_GAP_PT


# isometric overview key: center height above the axes bottom, swatch size,
# swatch-to-label gap and entry-to-entry gap, all in points
ROW_KEY_Y_PT = 18.0
ROW_KEY_SWATCH_PT = 9.0
ROW_KEY_TEXT_GAP_PT = 5.0
ROW_KEY_ENTRY_GAP_PT = 16.0


KEY_ROW_PT = 13.0
KEY_SWATCH_W_PT = 24.0
KEY_SWATCH_H_PT = 9.0


def _add_point_key(ax, items, below_pt):
    from matplotlib.patches import Circle, Rectangle
    fig = ax.figure
    ax.apply_aspect()
    # points -> display pixels, origin at the axes' lower-left corner; the
    # corner is looked up through transAxes at draw time, so the key moves
    # with the axes when bbox_inches="tight" shifts the figure
    to_px = (Affine2D().scale(1 / 72) + fig.dpi_scale_trans
             + ScaledTranslation(0, 0, ax.transAxes))
    x0 = 0.0
    y_top = -below_pt
    for i, (label, color, style) in enumerate(items):
        yc = y_top - i * KEY_ROW_PT
        kw = dict(fc=style.get("fc", "none"), ec=color, lw=style.get("lw", 0.9),
                  ls=style.get("ls", "-"), transform=to_px, clip_on=False,
                  zorder=5)
        if style.get("shape") == "circle":
            patch = Circle((x0 + KEY_SWATCH_W_PT / 2, yc),
                           KEY_SWATCH_H_PT / 2, **kw)
        else:
            patch = Rectangle((x0, yc - KEY_SWATCH_H_PT / 2),
                              KEY_SWATCH_W_PT, KEY_SWATCH_H_PT, **kw)
        ax.add_patch(patch)
        ax.text(x0 + KEY_SWATCH_W_PT + 6, yc, label, fontsize=7,
                color=DIM_COLOR, va="center", ha="left",
                fontfamily="sans-serif", transform=to_px, zorder=5)


# ---- plate diagram (isometric) ----
INSET_ZOOM = 6
INSET_FRAME_PAD_MM = 2.0


def _corner_rib_inset(ax, geom, S):
    """Enlarged view of the corner stacking rib ("Detail A").

    The rib is 6 x 1.5 mm, a few pixels at the diagram's scale. The inset
    redraws the origin corner (the only corner this view shows) at
    INSET_ZOOM times the diagram's scale, in the diagram's own data units,
    so its true magnification is exactly INSET_ZOOM. It is placed in the
    empty area above the plate's left corner, clear of every label.
    """
    from matplotlib.patches import Polygon as MplPoly
    K = S * INSET_ZOOM
    E = ISO_Z_EXAGGERATION
    ox, oy = geom.stack_xs[0], geom.stack_ys[0]
    hl, hw, h = geom.stack_len / 2, geom.stack_w / 2, geom.stack_h * E
    x1, y1 = ox + hl + INSET_FRAME_PAD_MM, oy + hw + INSET_FRAME_PAD_MM

    def p(x, y, z=0.0):
        return iso(x * K, y * K, z * K)

    def rect(xa, ya, xb, yb, z):
        return [p(xa, ya, z), p(xb, ya, z), p(xb, yb, z), p(xa, yb, z)]

    # the rib's faces are opaque: it stands in front of the corner's edges
    # and must hide them
    polys = [
        # corner of the top face; its two far edges are real plate edges
        (rect(0, 0, x1, y1, 0), _faint(SHAPE, 0.16), "none"),
        # rib: +x face, +y face (the two faces this view can see), top
        ([p(ox + hl, oy - hw, 0), p(ox + hl, oy + hw, 0),
          p(ox + hl, oy + hw, h), p(ox + hl, oy - hw, h)],
         _solid(AMBER, 0.55), FG),
        ([p(ox - hl, oy + hw, 0), p(ox + hl, oy + hw, 0),
          p(ox + hl, oy + hw, h), p(ox - hl, oy + hw, h)],
         _solid(AMBER, 0.4), FG),
        (rect(ox - hl, oy - hw, ox + hl, oy + hw, h), _solid(AMBER, 0.9), FG),
    ]
    pts = [pt for poly, _, _ in polys for pt in poly]
    pad = 8
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    bx0, bx1, by0, by1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad

    # place: left edge of the diagram's data, top of it, in data units of
    # the main axes (so the box is exactly the content size and the
    # magnification is exactly INSET_ZOOM)
    ax.autoscale_view()
    xl, yl = ax.get_xlim(), ax.get_ylim()
    w, hgt = bx1 - bx0, by1 - by0
    left, top = xl[0], yl[1] - 0.06 * (yl[1] - yl[0])
    axin = ax.inset_axes([left, top - hgt, w, hgt], transform=ax.transData)
    axin.set_xlim(bx0, bx1)
    axin.set_ylim(by0, by1)
    axin.set_aspect("equal", adjustable="box")
    axin.set_xticks([])
    axin.set_yticks([])
    axin.set_facecolor(BG)
    for spine in axin.spines.values():
        spine.set_edgecolor(FG)
        spine.set_linewidth(0.7)
    # corner fill, then its edges, then the rib on top of both
    for i, (pts_, fc, ec) in enumerate(polys):
        axin.add_patch(MplPoly(pts_, fc=fc, ec=ec, lw=0.7, zorder=1 if i == 0 else 3))
    # solid: the plate's real edges; dashed: where the corner is cut away
    axin.plot(*zip(p(x1, 0), p(0, 0), p(0, y1)), color=FG, lw=0.8, zorder=2)
    axin.plot(*zip(p(x1, 0), p(x1, y1), p(0, y1)), color=MUTED, lw=0.7,
              ls=(0, (3, 2)), zorder=2)
    axin.text(0.5, 1.03,
              f"Detail A, \u00d7{INSET_ZOOM}: corner stacking rib\n"
              f"{geom.stack_len:g} \u00d7 {geom.stack_w:g} mm, "
              f"{geom.stack_h:g} mm tall (height \u00d7{E} as above)",
              transform=axin.transAxes, ha="center", va="bottom",
              fontsize=7.5, color=FG, fontfamily="sans-serif")
    # label the rib itself so the detail doesn't rely on color
    axin.annotate("rib", xy=p(ox + hl, oy, h / 2), xytext=(-24, -30),
                  textcoords="offset points", fontsize=7.5, color=FG,
                  fontfamily="sans-serif", ha="right", va="top",
                  arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))


def _plate_diagram(out_path, geom):
    from matplotlib.patches import Polygon as MplPoly, Circle as MplCircle
    S = 1.8
    fig, ax = plt.subplots(figsize=(12, 8.5), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    px, py, pz = geom.plate_x * S, geom.plate_y * S, geom.plate_z * S * ISO_Z_EXAGGERATION

    ax.add_patch(MplPoly(iso_rect(0, 0, px, py, pz),
                 fc=_faint(SHAPE, 0.16), ec=FG, lw=0.5, zorder=2))
    ax.add_patch(MplPoly(iso_right_face(px, 0, py, 0, pz),
                 fc=_faint(SHAPE, 0.42), ec=FG, lw=0.5, zorder=2))
    ax.add_patch(MplPoly(iso_back_face(0, px, py, 0, pz),
                 fc=_faint(SHAPE, 0.30), ec=FG, lw=0.5, zorder=2))

    # magnet positions, for reference -- on the back (y=plate_y) face,
    # since that's the one actually rendered as a side wall below (the
    # mirror-image front face at y=0 is never drawn in this view)
    for mx in geom.mag_xs:
        mag_pt = iso(mx * S, py, pz * 0.5)
        ax.add_patch(MplCircle(mag_pt, 3.5, fc=_faint(VIOLET, 0.6),
                     ec=FG, lw=0.4, zorder=4))

    # corner stacking rib footprint, top-left-front corner, for reference
    sx0, sy0 = geom.stack_xs[0] * S, geom.stack_ys[0] * S
    ax.add_patch(MplPoly(
        iso_rect(sx0 - geom.stack_len * S / 2, sy0 - geom.stack_w * S / 2,
                 sx0 + geom.stack_len * S / 2, sy0 + geom.stack_w * S / 2, pz),
        fc=_faint(AMBER, 0.7), ec=FG, lw=0.6, zorder=4))

    top_ctr = iso(px / 2, py / 2, pz)
    ax.text(top_ctr[0], top_ctr[1], "Top face",
            fontsize=9, fontweight="bold", color=FG,
            ha="center", va="center", zorder=6)

    # only the top, right (x=plate_x), and back (y=plate_y) faces are
    # actually drawn in this view -- the mirror-image left/front faces
    # are never rendered, so their labels point at the visible face and
    # say where the mirrored copy lives instead of anchoring on
    # undrawn geometry (a past bug: leaders for "Front edge"/"Left edge"
    # anchored at y=0/x=0, points that project into the same screen area
    # as the visible faces even though they aren't actually on them).
    right_pt = iso(px, py * 0.55, pz * 0.35)
    leader(ax, right_pt, (right_pt[0] - 80, right_pt[1] + 10),
           "Right edge (branding, mirrored on the left)", ha="right",
           dashed=False)

    # anchored left of the "Magnet bore" bore (see below), so this leader
    # runs under that one instead of crossing it
    back_pt = iso(px * 0.45, py, pz * 0.35)
    leader(ax, back_pt, (back_pt[0] + 70, back_pt[1] - 55),
           "Back edge (magnets, mirrored on the front)", dashed=False)

    bottom_pt = iso(px / 2, py, 0)
    # label sits below the part (the back face's bottom edge slopes up to
    # the right), so neither it nor its leader runs over the plate
    leader(ax, bottom_pt, (bottom_pt[0] + 40, bottom_pt[1] - 75),
           "Bottom — sits on the bed, carries mounting magnets")

    mag_pt = iso(geom.mag_xs[1] * S, py, pz * 0.5)
    # label placed past the plate's right end so the text itself is clear
    # of the part; the leader still reaches the bore
    leader(ax, mag_pt, (mag_pt[0] + 135, mag_pt[1] + 10),
           "Magnet bore")

    # the rib is a few pixels at this scale, so the leader points at a
    # dashed frame around it (anchor dot on the frame, off the rib) and the
    # frame is drawn enlarged in the "Detail A" inset
    pad = INSET_FRAME_PAD_MM * S
    hl, hw = geom.stack_len * S / 2, geom.stack_w * S / 2
    frame = iso_rect(sx0 - hl - pad, sy0 - hw - pad,
                     sx0 + hl + pad, sy0 + hw + pad, pz)
    ax.add_patch(MplPoly(frame, fc="none", ec=FG, lw=0.7, ls=(0, (2, 1.5)),
                         zorder=5))
    stack_pt = iso(sx0 - hl - pad, sy0 + hw + pad, pz)  # rightmost corner
    leader(ax, stack_pt, (stack_pt[0] + 60, stack_pt[1] + 55),
           "Corner stacking rib A\n(groove on underside)")
    _corner_rib_inset(ax, geom, S)

    # sits 1 pt above the axes' bottom edge, under the key row (which is
    # centered at ROW_KEY_Y_PT) and clear of the plate's lowest corner
    ax.annotate(
        f"Vertical scale ×{ISO_Z_EXAGGERATION}: plate thickness and "
        "bore heights are exaggerated; X and Y are to scale",
        xy=(0.01, 0), xycoords="axes fraction", xytext=(0, 1),
        textcoords="offset points", fontsize=7.5, ha="left", va="bottom",
        color=MUTED, fontfamily="sans-serif", fontstyle="italic")

    ax.autoscale_view()
    ax.margins(0.08)
    add_key(ax, [
        ("plate", SHAPE), ("magnets", VIOLET), ("stacking rib", AMBER),
    ])
    _save_png(fig, out_path, dpi=200, bbox_inches="tight", pad_inches=0.3,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


# -------- technical drawings --------
DIM_COLOR = "#333333"
DIM_LW = 0.6
EXT_LW = 0.4
HATCH_COLOR = "#666666"
HATCH_LW = 0.3
CUT_LW = 1.2
HIDDEN_LW = 0.5
HIDDEN_LS = (0, (4, 2))
# hidden magnet bores are dotted, hidden grooves dashed, so the two differ
# by line pattern and not only by color (WCAG 1.4.1); a little heavier so
# the dots read at 3:1 and at README width
HIDDEN_BORE_LS = (0, (1, 1.5))
HIDDEN_BORE_LW = 0.9
# dimension text interrupts whatever it crosses, as on a real drawing
_DIM_LABEL_BBOX = dict(facecolor=BG, edgecolor="none", pad=0.15)


def _dim_h(ax, y, x0, x1, label, offset=0, fontsize=MIN_LABEL_PT, side="above",
           outside=False):
    # outside=True for spans narrower than a pair of arrowheads, which would
    # otherwise meet in the middle and read as a bowtie: the arrowheads sit
    # outside the extension lines and point in (ISO 129 small-space style)
    oy = y + offset
    gap = 1.2 if side == "above" else -1.2
    if outside:
        ax.plot([x0, x1], [oy, oy], color=DIM_COLOR, lw=DIM_LW)
        for x, dx in ((x0, -14), (x1, 14)):
            ax.annotate("", xy=(x, oy), xytext=(dx, 0),
                        textcoords="offset points",
                        arrowprops=dict(arrowstyle="->", color=DIM_COLOR,
                                        lw=DIM_LW, shrinkA=0, shrinkB=0))
    else:
        ax.annotate("", xy=(x0, oy), xytext=(x1, oy),
                    arrowprops=dict(arrowstyle="<->", color=DIM_COLOR,
                                    lw=DIM_LW, shrinkA=0, shrinkB=0))
    ax.plot([x0, x0], [y, oy], color=DIM_COLOR, lw=EXT_LW)
    ax.plot([x1, x1], [y, oy], color=DIM_COLOR, lw=EXT_LW)
    if outside:
        # the outside arrowheads flank the label, so offset it clear of
        # them in points (a data-unit gap is too small at this scale)
        ax.annotate(label, xy=((x0 + x1) / 2, oy),
                    xytext=(0, 6 if side == "above" else -6),
                    textcoords="offset points", fontsize=fontsize,
                    ha="center", va="bottom" if side == "above" else "top",
                    color=DIM_COLOR, fontfamily="sans-serif", zorder=7,
                    bbox=_DIM_LABEL_BBOX)
        return
    ax.text((x0 + x1) / 2, oy + gap, label, fontsize=fontsize,
            ha="center", va="bottom" if side == "above" else "top",
            color=DIM_COLOR, fontfamily="sans-serif", zorder=7,
            bbox=_DIM_LABEL_BBOX)


def _dim_v(ax, x, y0, y1, label, offset=0, fontsize=MIN_LABEL_PT, side="right"):
    ox = x + offset
    gap = 1.2 if side == "right" else -1.2
    ax.annotate("", xy=(ox, y0), xytext=(ox, y1),
                arrowprops=dict(arrowstyle="<->", color=DIM_COLOR,
                                lw=DIM_LW, shrinkA=0, shrinkB=0))
    ax.plot([x, ox], [y0, y0], color=DIM_COLOR, lw=EXT_LW)
    ax.plot([x, ox], [y1, y1], color=DIM_COLOR, lw=EXT_LW)
    ax.text(ox + gap, (y0 + y1) / 2, label, fontsize=fontsize,
            ha="left" if side == "right" else "right",
            va="center", color=DIM_COLOR, fontfamily="sans-serif",
            rotation=90, zorder=7, bbox=_DIM_LABEL_BBOX)


def _fit_view(*axes, pad=0.05):
    # dataLim tracks patches and lines but never text, so every dimension
    # label sits outside it and naive autoscaling crops them; union the
    # labels' rendered extents in first. Measuring costs a full draw, so
    # fit every axes off the one draw.
    from matplotlib.transforms import Bbox
    fig = axes[0].figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for ax in axes:
        inv = ax.transData.inverted()
        extent = Bbox(ax.dataLim.get_points().copy())
        for label in ax.texts:
            if label.get_transform() is ax.transAxes:
                continue  # captions are pinned to the box on purpose
            box_ = label.get_window_extent(renderer)
            extent = Bbox.union([extent, box_.transformed(inv)])
        dx, dy = extent.width * pad, extent.height * pad
        ax.set_xlim(extent.x0 - dx, extent.x1 + dx)
        ax.set_ylim(extent.y0 - dy, extent.y1 + dy)


def _hatch_fill(ax, clip, cx, cy, diag, angle, spacing):
    # autolim=False: the lines overhang the clip patch by design, and a clip
    # path is applied at draw time only — letting them reach dataLim inflates
    # it to a 45-degree square and collapses any axes that autoscales.
    from matplotlib.collections import LineCollection
    n = int(diag / spacing) + 1
    rad = np.radians(angle)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    d = np.arange(-n, n + 1) * spacing
    start = np.column_stack([cx + d * cos_a - diag * sin_a,
                             cy + d * sin_a + diag * cos_a])
    end = np.column_stack([cx + d * cos_a + diag * sin_a,
                           cy + d * sin_a - diag * cos_a])
    lc = LineCollection(np.stack([start, end], axis=1), colors=HATCH_COLOR,
                        linewidths=HATCH_LW, zorder=2)
    lc.set_clip_path(clip)
    ax.add_collection(lc, autolim=False)


def _hatch_rect(ax, x0, y0, x1, y1, angle=45, spacing=1.5):
    from matplotlib.patches import Polygon as MplPoly
    clip = MplPoly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True,
                   transform=ax.transData)
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    diag = np.sqrt(dx**2 + dy**2) * 1.5
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    _hatch_fill(ax, clip, cx, cy, diag, angle, spacing)


def _title_block(ax, title):
    # below the axes, not inside it: on a wide flat view like the front
    # elevation the box is short enough that an inset caption lands on
    # the drawing.
    #
    # No "Scale N:1" here (and none on the other drawings either): S is
    # just the mm-to-plot-units multiplier used to build the coordinates
    # handed to matplotlib, and every one of these axes is equal-aspect
    # and autoscaled to fit the figure -- so S cancels out of the
    # rendered image entirely and any "Scale" figure quoting it is
    # fiction (measured on the actual renders: labeled 2:1, 10:1, 45:1
    # and 22:1, actual were closer to 0.74:1, 1.2:1, 5:1 and 5:1). A
    # screen render doesn't have a meaningful physical scale to state;
    # the dimension figures on the drawing itself are what's accurate.
    ax.text(0.99, -0.08, f"{title}  |  v{VERSION}",
            transform=ax.transAxes, fontsize=7, ha="right", va="top",
            color=MUTED, fontfamily="sans-serif")


# Feature keys for the top plan and the front elevation. Each swatch uses
# the line style the feature is drawn in, and each label names the feature
# and the face it is on, so the key does not rely on color.
KEY_GROOVE = ("dashed rectangle: stacking groove (hidden, bottom face)",
              FG, dict(ls=HIDDEN_LS))
KEY_RIB = ("solid filled rectangle: stacking rib (top face)",
           FG, dict(fc=_faint(AMBER, 0.6), lw=0.6))
KEY_BOTTOM_BORE_CIRCLE = (
    "dotted circle: mounting magnet bore (hidden, bottom face)",
    VIOLET, dict(shape="circle", ls=HIDDEN_BORE_LS, lw=HIDDEN_BORE_LW))
KEY_BOTTOM_BORE_RECT = (
    "dotted rectangle: mounting magnet bore (hidden, bottom face)",
    VIOLET, dict(ls=HIDDEN_BORE_LS, lw=HIDDEN_BORE_LW))
KEY_EDGE_BORE = (
    "dotted rectangle at the edge: magnet bore (hidden, front and back faces)",
    VIOLET, dict(ls=HIDDEN_BORE_LS, lw=HIDDEN_BORE_LW))
KEY_FRONT_BORE = (
    "solid circle: magnet bore (front face)",
    VIOLET, dict(shape="circle", fc=_faint(VIOLET, 0.15), lw=0.8))
TOP_PLAN_KEY = [KEY_GROOVE, KEY_BOTTOM_BORE_CIRCLE, KEY_EDGE_BORE, KEY_RIB]
FRONT_KEY = [KEY_FRONT_BORE, KEY_BOTTOM_BORE_RECT, KEY_GROOVE, KEY_RIB]
FEATURE_KEY_GAP_PT = 26.0


# ---- technical drawing 1: dimensioned top plan view ----
def _tech_top_plan(out_path, geom):
    S = 2.0
    fig, ax = plt.subplots(figsize=(14, 10), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # plate outline
    ax.add_patch(plt.Rectangle((0, 0), geom.plate_x * S, geom.plate_y * S,
                 fc="none", ec=FG, lw=CUT_LW, zorder=3))

    # magnet bores (front and back faces) -- blind bores drilled
    # horizontally inward from the Y face, not through-holes, so seen
    # from directly above they project as a mag_d (X) x mag_depth (Y)
    # rectangle starting at the face and receding into the material,
    # not a circle centered on the edge (half of which would render
    # outside the part). Hidden from this top-down view past the
    # entrance, so dotted like the bottom-face bores below.
    for mx in geom.mag_xs:
        for y_face, into_sign in ((0.0, 1.0), (geom.plate_y, -1.0)):
            y0 = y_face if into_sign > 0 else y_face - geom.mag_depth
            ax.add_patch(plt.Rectangle(
                (mx * S - geom.mag_d * S / 2, y0 * S),
                geom.mag_d * S, geom.mag_depth * S,
                fc="none", ec=VIOLET, lw=HIDDEN_BORE_LW, ls=HIDDEN_BORE_LS, zorder=5))
            ax.plot(mx * S, y_face * S, "+", color=VIOLET, ms=3, mew=0.6,
                    zorder=5)

    # bottom-face mounting magnets: also hidden (blind, drilled straight
    # up from the underside), drawn dotted for the same reason
    for mx in (geom.bottom_mag_inset_x, geom.plate_x - geom.bottom_mag_inset_x):
        for my in geom.bottom_mag_ys:
            ax.add_patch(plt.Circle((mx * S, my * S), geom.mag_d * S / 2,
                         fc="none", ec=VIOLET, lw=HIDDEN_BORE_LW, ls=HIDDEN_BORE_LS,
                         zorder=5))
            ax.plot(mx * S, my * S, "+", color=VIOLET, ms=3, mew=0.6,
                    zorder=5)

    # corner stacking ribs (top face, visible) / grooves (bottom face,
    # hidden -- dashed, unlike the dotted bores above)
    for mx in geom.stack_xs:
        for my in geom.stack_ys:
            groove_len = geom.stack_len + geom.stack_play
            groove_w = geom.stack_w + geom.stack_play
            ax.add_patch(plt.Rectangle(
                (mx * S - groove_len * S / 2, my * S - groove_w * S / 2),
                groove_len * S, groove_w * S,
                fc="none", ec=FG, lw=HIDDEN_LW, ls=HIDDEN_LS, zorder=4))
            ax.add_patch(plt.Rectangle(
                (mx * S - geom.stack_len * S / 2, my * S - geom.stack_w * S / 2),
                geom.stack_len * S, geom.stack_w * S,
                fc=_faint(AMBER, 0.6), ec=FG, lw=0.6, zorder=5))

    # debossed logo + label on the top face (front band): footprint only,
    # from the same bounds build_plate() validated and cut
    bx0, by0, bx1, by1 = geom.top_branding_bounds
    ax.add_patch(plt.Rectangle(
        (bx0 * S, by0 * S), (bx1 - bx0) * S, (by1 - by0) * S,
        fc=_faint(SHAPE, 0.25), ec=MUTED, lw=0.6, zorder=4))
    ax.text((bx0 + bx1) / 2 * S, (by0 + by1) / 2 * S,
            "branding", fontsize=MIN_LABEL_PT,
            ha="center", va="center", color=FG, fontfamily="sans-serif",
            zorder=6)

    # overall dimensions
    _dim_h(ax, geom.plate_y * S, 0, geom.plate_x * S,
           f"{geom.plate_x:.0f}", offset=12 * S)
    _dim_v(ax, geom.plate_x * S, 0, geom.plate_y * S,
           f"{geom.plate_y:.0f}", offset=12 * S)

    # front border band (houses the bottom mounting magnet + branding)
    _dim_v(ax, 0, 0, geom.front_margin * S,
           f"{geom.front_margin:.0f}", offset=-15 * S, side="left")

    # magnet X positions
    ax.annotate("", xy=(geom.mag_xs[0] * S, -6 * S),
                xytext=(geom.mag_xs[1] * S, -6 * S),
                arrowprops=dict(arrowstyle="<->", color=VIOLET, lw=DIM_LW,
                                shrinkA=0, shrinkB=0))
    ax.plot([geom.mag_xs[0] * S, geom.mag_xs[0] * S], [0, -6 * S],
            color=VIOLET, lw=EXT_LW)
    ax.plot([geom.mag_xs[1] * S, geom.mag_xs[1] * S], [0, -6 * S],
            color=VIOLET, lw=EXT_LW)
    ax.text((geom.mag_xs[0] + geom.mag_xs[1]) / 2 * S, -7.5 * S,
            f"{geom.mag_xs[1] - geom.mag_xs[0]:.1f} typ.",
            fontsize=MIN_LABEL_PT, ha="center", va="top", color=DIM_COLOR,
            fontfamily="sans-serif")

    # stacking rib inset from the left edge
    _dim_h(ax, geom.stack_ys[0] * S - geom.stack_w * S, 0, geom.stack_xs[0] * S,
           f"{geom.stack_inset_x:.0f}", offset=-8 * S, side="below",
           fontsize=MIN_LABEL_PT, outside=True)

    _title_block(ax, "Top Plan View")

    ax.autoscale_view()
    ax.margins(0.06)
    add_key(ax, TOP_PLAN_KEY, below_pt=FEATURE_KEY_GAP_PT)
    _save_png(fig, out_path, dpi=200, bbox_inches="tight", pad_inches=0.4,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


# ---- technical drawing 2: front elevation (Y=0 face) ----
def _tech_front_elevation(out_path, geom):
    S = 10.0
    fig, ax = plt.subplots(figsize=(12, 2.6), dpi=200)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # plate outline (front face: X vs Z, true scale)
    ax.add_patch(plt.Rectangle((0, 0), geom.plate_x * S, geom.plate_z * S,
                 fc=_faint(SHAPE, 0.08), ec=FG, lw=CUT_LW, zorder=3))

    # corner stacking ribs -- raised above the top face near each edge;
    # visible (not hidden) in this view, nothing else stands taller
    for rib_cx in geom.stack_xs:
        ax.add_patch(plt.Rectangle(
            ((rib_cx - geom.stack_len / 2) * S, geom.plate_z * S),
            geom.stack_len * S, geom.stack_h * S,
            fc=_faint(AMBER, 0.55), ec=FG, lw=CUT_LW, zorder=4,
        ))

    # magnet bores (front face, true circles)
    for mx in geom.mag_xs:
        bore_cx = mx * S
        bore_cy = (geom.plate_z / 2) * S
        bore_r = (geom.mag_d / 2) * S
        ax.add_patch(plt.Circle((bore_cx, bore_cy), bore_r,
                     fc=_faint(VIOLET, 0.15), ec=VIOLET, lw=0.8, zorder=4))
        ax.plot(bore_cx, bore_cy, "+", color=VIOLET, ms=4, mew=0.5, zorder=5)

    # hidden features, dashed (standard hidden-line convention): the
    # bottom-face corner mounting bores and the stacking grooves, both
    # cut up from the underside and so invisible from the front
    for bore_cx in (geom.bottom_mag_inset_x,
                    geom.plate_x - geom.bottom_mag_inset_x):
        ax.add_patch(plt.Rectangle(
            ((bore_cx - geom.mag_d / 2) * S, 0),
            geom.mag_d * S, geom.mag_depth * S,
            fc="none", ec=VIOLET, lw=HIDDEN_BORE_LW, ls=HIDDEN_BORE_LS, zorder=5))
    for groove_cx in geom.stack_xs:
        groove_len = geom.stack_len + geom.stack_play
        ax.add_patch(plt.Rectangle(
            ((groove_cx - groove_len / 2) * S, 0),
            groove_len * S, (geom.stack_h + geom.stack_play) * S,
            fc="none", ec=FG, lw=HIDDEN_LW, ls=HIDDEN_LS, zorder=5))

    # overall X dimension (above)
    _dim_h(ax, geom.plate_z * S, 0, geom.plate_x * S,
           f"{geom.plate_x:.0f}", offset=6 * S)

    # overall Z dimension (right)
    _dim_v(ax, geom.plate_x * S, 0, geom.plate_z * S,
           f"{geom.plate_z:.0f}", offset=8 * S)

    # magnet bore center height, outside the plate (6 mm left of its end)
    # with an extension line from the first bore's center, so the label
    # touches no outline
    _dim_v(ax, geom.mag_xs[0] * S, 0, (geom.plate_z / 2) * S,
           f"{geom.plate_z / 2:.1f}", offset=-(geom.mag_xs[0] + 6) * S,
           side="left")

    _title_block(ax, "Front Elevation")

    ax.autoscale_view()
    ax.margins(x=0.03, y=0.15)
    add_key(ax, FRONT_KEY, below_pt=FEATURE_KEY_GAP_PT)
    _save_png(fig, out_path, dpi=200, bbox_inches="tight", pad_inches=0.3,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


# ---- technical drawing 3: magnet-bore and stacking-joint detail ----
def _tech_detail(out_path, geom, magnet_d=MAGNET_D, magnet_len=MAGNET_LEN):
    from matplotlib.patches import Polygon as MplPoly
    import matplotlib.gridspec as gridspec

    fig = plt.figure(figsize=(14, 6), dpi=200)
    fig.patch.set_facecolor(BG)
    gs = gridspec.GridSpec(1, 2, wspace=0.2)

    # ---- left: magnet bore detail (front/back face, Y-Z plane) ----
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_aspect("equal")
    ax1.axis("off")
    ax1.set_facecolor(BG)

    S1 = 45.0
    mat_y0 = 0.0  # front/back face -- material starts here, never before it
    leader_y0 = -2.0  # dashed centerline only, extends past the face for clarity
    plate_y1_m = geom.mag_depth + 8.0
    bore_r = geom.mag_d / 2
    mag_cz = geom.plate_z / 2

    # left (y=0, mat_y0) is the plate's real front/back face -- drawn
    # solid. Right (y=plate_y1_m) is just where this window stops, not a
    # real edge (the actual opposite face is at y=plate_y, off-screen) --
    # drawn as a break so it doesn't read as one. Same fix as the
    # stacking-joint panel got in 5892a23.
    plate_verts = [
        (mat_y0, 0), (plate_y1_m, 0),
        (plate_y1_m, geom.plate_z), (mat_y0, geom.plate_z),
    ]
    ax1.add_patch(MplPoly([(y * S1, z * S1) for y, z in plate_verts],
                  fc=_faint(SHAPE, 0.10), ec="none", zorder=2))
    ax1.plot([mat_y0 * S1, plate_y1_m * S1], [0, 0], color=FG, lw=CUT_LW,
             zorder=3)
    ax1.plot([mat_y0 * S1, plate_y1_m * S1], [geom.plate_z * S1] * 2,
             color=FG, lw=CUT_LW, zorder=3)
    ax1.plot([mat_y0 * S1, mat_y0 * S1], [0, geom.plate_z * S1],
             color=FG, lw=CUT_LW, zorder=3)
    ax1.plot([plate_y1_m * S1, plate_y1_m * S1], [0, geom.plate_z * S1],
             color=MUTED, lw=0.6, ls=(0, (2, 1.5)), zorder=3)
    _hatch_rect(ax1, mat_y0 * S1, 0, plate_y1_m * S1,
                (mag_cz - bore_r) * S1, spacing=4.5)
    _hatch_rect(ax1, mat_y0 * S1, (mag_cz + bore_r) * S1,
                plate_y1_m * S1, geom.plate_z * S1, spacing=4.5)
    _hatch_rect(ax1, geom.mag_depth * S1, (mag_cz - bore_r) * S1,
                plate_y1_m * S1, (mag_cz + bore_r) * S1, spacing=4.5)

    bore_verts = [
        (0, mag_cz - bore_r), (geom.mag_depth, mag_cz - bore_r),
        (geom.mag_depth, mag_cz + bore_r), (0, mag_cz + bore_r),
    ]
    ax1.add_patch(MplPoly([(y * S1, z * S1) for y, z in bore_verts],
                  fc=BG, ec=FG, lw=CUT_LW, zorder=3))

    magnet_r = magnet_d / 2
    mag_verts = [
        (0, mag_cz - magnet_r), (magnet_len, mag_cz - magnet_r),
        (magnet_len, mag_cz + magnet_r), (0, mag_cz + magnet_r),
    ]
    ax1.add_patch(MplPoly([(y * S1, z * S1) for y, z in mag_verts],
                  fc=_faint(VIOLET, 0.2), ec=VIOLET, lw=0.8,
                  ls="--", zorder=4))
    ax1.text(magnet_len / 2 * S1, mag_cz * S1,
             f"magnet\n{magnet_d:g}×{magnet_len:g}",
             fontsize=MIN_LABEL_PT, ha="center", va="center", color=VIOLET_TEXT,
             fontfamily="sans-serif", fontstyle="italic", zorder=5)

    ax1.plot([leader_y0 * S1, plate_y1_m * S1],
             [mag_cz * S1, mag_cz * S1],
             color=DIM_COLOR, lw=0.4, ls=(0, (8, 4)), zorder=2)

    _dim_v(ax1, geom.mag_depth / 2 * S1, (mag_cz - bore_r) * S1,
           (mag_cz + bore_r) * S1,
           f"⌀{geom.mag_d:.1f}", offset=5 * S1, fontsize=7)
    _dim_h(ax1, (mag_cz + bore_r) * S1, 0, geom.mag_depth * S1,
           f"{geom.mag_depth:.1f} deep", offset=3 * S1, fontsize=7)
    _dim_v(ax1, plate_y1_m * S1, 0, mag_cz * S1,
           f"{mag_cz:.1f}", offset=4 * S1, fontsize=MIN_LABEL_PT)
    _dim_v(ax1, plate_y1_m * S1, 0, geom.plate_z * S1,
           f"{geom.plate_z:.0f}", offset=9 * S1, fontsize=7)
    clearance = geom.mag_depth - magnet_len
    if clearance > 0.05:
        # arrowheads outside: the span is narrower than a pair of them
        _dim_h(ax1, (mag_cz - bore_r) * S1, magnet_len * S1, geom.mag_depth * S1,
               f"{clearance:.1f}", offset=-3 * S1, side="below",
               fontsize=MIN_LABEL_PT, outside=True)

    ax1.text(0.5, -0.02,
             "Magnet Bore Detail",
             transform=ax1.transAxes, fontsize=7, ha="center", va="top",
             color=MUTED, fontfamily="sans-serif", fontweight="bold")

    # ---- right: stacking rib/groove joint detail (X-Z plane, one corner) ----
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_facecolor(BG)

    S2 = 22.0
    # window's left edge is clamped to the plate's real X extent (it ran
    # past x=0 at the default stack_inset_x=4mm, hatching air as solid).
    # The right edge now extends past the bottom-corner mounting bore's
    # far edge, plus a margin, so this view can show the bore and the
    # magnet-bore-to-groove wall the stack coupon exists to validate --
    # it used to stop just short of the bore (hiding it) and draw that
    # stopping point as if it were a real plate edge.
    det_x0 = max(0.0, geom.stack_xs[0] - geom.stack_len / 2 - 4.0)
    bore_x = geom.bottom_mag_inset_x
    det_x1 = min(geom.plate_x, bore_x + geom.mag_d / 2 + 4.0)
    # whether each boundary is the plate's actual edge (drawn solid) or
    # just where this window stops (drawn as a break, not a real edge)
    left_is_real_edge = det_x0 <= 1e-9
    right_is_real_edge = det_x1 >= geom.plate_x - 1e-9

    # this plate's body: bottom face carries the recessed groove, top face
    # carries the raised rib -- both are the same solid, shown together so
    # the joint is legible without drawing a second mating plate
    body_verts = [
        (det_x0, 0), (det_x1, 0), (det_x1, geom.plate_z), (det_x0, geom.plate_z),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in body_verts],
                  fc=_faint(SHAPE, 0.10), ec="none", zorder=2))
    _hatch_rect(ax2, det_x0 * S2, 0, det_x1 * S2, geom.plate_z * S2,
                spacing=4.0)
    # top/bottom are always real plate faces (solid); left/right are only
    # real plate edges when the window is clamped there -- otherwise
    # they're just where this window stops, drawn as a break so they
    # don't read as an actual edge of the part
    ax2.plot([det_x0 * S2, det_x1 * S2], [0, 0], color=FG, lw=CUT_LW, zorder=3)
    ax2.plot([det_x0 * S2, det_x1 * S2], [geom.plate_z * S2] * 2,
             color=FG, lw=CUT_LW, zorder=3)
    for x, is_real in ((det_x0, left_is_real_edge), (det_x1, right_is_real_edge)):
        style = dict(color=FG, lw=CUT_LW) if is_real else dict(
            color=MUTED, lw=0.6, ls=(0, (2, 1.5)))
        ax2.plot([x * S2, x * S2], [0, geom.plate_z * S2], zorder=3, **style)

    rib_x0 = geom.stack_xs[0] - geom.stack_len / 2
    rib_x1 = geom.stack_xs[0] + geom.stack_len / 2
    rib_verts = [
        (rib_x0, geom.plate_z), (rib_x1, geom.plate_z),
        (rib_x1, geom.plate_z + geom.stack_h), (rib_x0, geom.plate_z + geom.stack_h),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in rib_verts],
                  fc=_faint(AMBER, 0.55), ec=FG, lw=CUT_LW, zorder=4))

    play = geom.stack_play / 2
    groove_depth = geom.stack_h + geom.stack_play
    groove_verts = [
        (rib_x0 - play, 0), (rib_x1 + play, 0),
        (rib_x1 + play, groove_depth), (rib_x0 - play, groove_depth),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in groove_verts],
                  fc=BG, ec=FG, lw=CUT_LW, zorder=4))

    ax2.text(geom.stack_xs[0] * S2, (geom.plate_z + geom.stack_h + 0.8) * S2,
             "rib (top face)", fontsize=MIN_LABEL_PT, ha="center", va="bottom",
             color=AMBER_TEXT, fontfamily="sans-serif", fontstyle="italic",
             zorder=5)
    ax2.text(geom.stack_xs[0] * S2, (groove_depth / 2) * S2,
             "groove\n(bottom face)", fontsize=MIN_LABEL_PT, ha="center", va="center",
             color=MUTED, fontfamily="sans-serif", fontstyle="italic",
             zorder=5)

    _dim_v(ax2, rib_x1 * S2, geom.plate_z * S2, (geom.plate_z + geom.stack_h) * S2,
           f"{geom.stack_h:.1f}", offset=4 * S2, fontsize=7)
    _dim_h(ax2, geom.plate_z * S2, rib_x0 * S2, rib_x1 * S2,
           f"{geom.stack_len:.1f}", offset=-2.5 * S2, side="below",
           fontsize=MIN_LABEL_PT)
    _dim_v(ax2, (rib_x0 - play) * S2, 0, groove_depth * S2,
           f"{groove_depth:.1f} deep", offset=-4 * S2, side="left",
           fontsize=MIN_LABEL_PT)

    # groove-to-plate-edge clearance (0.9 mm at the defaults) -- computed
    # from the actual geometry, not a hardcoded figure, so it can't drift
    # out of sync with stack_inset_x/stack_len/stack_play the way a
    # comment repeating this number elsewhere could.
    groove_edge_clearance = (rib_x0 - play) - det_x0
    _dim_h(ax2, 0, det_x0 * S2, (rib_x0 - play) * S2,
           f"{groove_edge_clearance:.1f}", offset=3 * S2, fontsize=MIN_LABEL_PT)

    # bottom-corner mounting bore -- sectioned through its own center, so
    # the vertical cylinder shows as a mag_d (X) x mag_depth (Z) rectangle
    # sitting on the bottom face, same convention the magnet-bore-detail
    # panel (left) uses for the horizontal push-fit bores. This is the
    # feature the stack coupon actually exists to validate the wall to;
    # a previous version of this view stopped just short of it (hiding
    # it) and drew that stopping point as if it were a real plate edge.
    bore_x0 = bore_x - geom.mag_d / 2
    bore_x1 = bore_x + geom.mag_d / 2
    bore_verts = [
        (bore_x0, 0), (bore_x1, 0),
        (bore_x1, geom.mag_depth), (bore_x0, geom.mag_depth),
    ]
    ax2.add_patch(MplPoly([(x * S2, z * S2) for x, z in bore_verts],
                  fc=BG, ec=FG, lw=CUT_LW, zorder=4))
    ax2.text(bore_x * S2, (geom.mag_depth / 2) * S2,
             "magnet bore\n(bottom face)", fontsize=MIN_LABEL_PT, ha="center",
             va="center", color=MUTED, fontfamily="sans-serif",
             fontstyle="italic", zorder=5)

    # magnet-bore-to-stacking-groove wall (1.85 mm at the defaults) --
    # the dimension the stack coupon exists to validate. Placed above
    # both features (groove and bore) to keep clear of either.
    wall = bore_x0 - (rib_x1 + play)
    _wall_dim_z = max(groove_depth, geom.mag_depth) + 1.5
    _dim_h(ax2, 0, (rib_x1 + play) * S2, bore_x0 * S2,
           f"{wall:.2f}", offset=_wall_dim_z * S2, fontsize=MIN_LABEL_PT)

    ax2.text(0.5, -0.02,
             "Stacking Joint Detail",
             transform=ax2.transAxes, fontsize=7, ha="center", va="top",
             color=MUTED, fontfamily="sans-serif", fontweight="bold")
    ax2.text(0.5, -0.10,
             "composite view: groove and bore shown at their own Y "
             "positions, not a single cross-section plane",
             transform=ax2.transAxes, fontsize=MIN_LABEL_PT, ha="center", va="top",
             color=MUTED, fontfamily="sans-serif", fontstyle="italic")

    _fit_view(ax1, ax2)

    _save_png(fig, out_path, dpi=200, bbox_inches="tight", pad_inches=0.3,
                facecolor=BG)
    plt.close(fig)
    print("wrote", out_path)


def _output_stem(printer_name=None):
    """Filename stem shared by every output file: `jig_plate_<VERSION>`,
    plus `_<printer>` (the canonical profile name, so an alias like h2d
    gives h2d-left) when a printer was chosen, so builds for different
    printers sit side by side instead of overwriting each other. With no
    printer it is exactly `jig_plate_<VERSION>`."""
    stem = f"jig_plate_{VERSION}"
    return stem if printer_name is None else f"{stem}_{printer_name}"


def _mesh_summary(name, mesh, volume_digits, bbox_digits):
    """One labeled console line per mesh, the same shape for both:
    `plate        | watertight: True | volume cm3: 481.5 | bbox: [...] | faces: N`
    (the name padded to the longest, "stack coupon")."""
    return (
        f"{name:<12} | watertight: {mesh.is_watertight} | "
        f"volume cm3: {round(mesh.volume / 1000, volume_digits)} | "
        f"bbox: {np.round(mesh.bounds[1] - mesh.bounds[0], bbox_digits)} | "
        f"faces: {len(mesh.faces)}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate the jig plate base STL, diagram, and "
                     "technical drawings."
    )
    parser.add_argument(
        "--label", default="Jig Plate",
        help='Text debossed on the top, left, and right faces, next to '
             'the logo mark (the logo itself is not parameterized). '
             'Default: "Jig Plate".',
    )
    parser.add_argument(
        "--printer", default=None, metavar="NAME",
        help="Bambu Lab printer to size the plate for: "
             + ", ".join(printer_names())
             + ". Sets the default plate size to that printer's usable "
             "print area (the largest keep-out-clear rectangle less 10 mm "
             "per axis) and rejects a plate that does not fit it. "
             "Dual-nozzle printers have one profile per nozzle; a bare "
             "x2d, h2d or h2c means the larger (left) nozzle. Only size "
             "is checked, not bed position. The printer's name is added to "
             "the output file names and the STL headers. Default: none, a "
             "246 x 218 mm plate with X capped at 246 mm.",
    )
    args = parser.parse_args()

    try:
        result = build_plate(label=args.label, printer=args.printer)
    except ValueError as e:
        parser.error(str(e))
    solid = result.solid
    geom = result.geometry
    # canonical profile name (aliases resolved), or None with no printer
    printer_name = (None if args.printer is None
                    else get_printer_profile(args.printer).name)
    stem = _output_stem(printer_name)
    tag = "" if printer_name is None else f"{printer_name} | "

    print(_mesh_summary("plate", solid, 1, 3))

    OUT_DIR.mkdir(exist_ok=True)
    OUT = OUT_DIR / f"{stem}.stl"
    _export_stl(
        solid, OUT,
        f"Jig plate {VERSION} | {tag}"
        f"{geom.plate_x:.0f}x{geom.plate_y:.0f}x{geom.plate_z + geom.stack_h:.1f}mm | "
        f"base plate, no pockets",
    )
    print("wrote", OUT)

    # test coupon: front-right corner, carrying the stacking rib/groove,
    # its bottom mounting magnet, AND (at the default mag_xs) the
    # rightmost front push-fit magnet bore, which also falls inside this
    # corner's cut region -- for validating the corner stacking fit and
    # the wall between the bottom mounting bore and the stacking
    # rib/groove (1.85 mm at the defaults), independently of any pocket
    # layout added later. Print two to mate. The cut region (46 x 20 mm)
    # is sized to fully contain the rib/groove and the bottom mounting
    # bore at the default stack_inset_x/_y and bottom_mag_inset_x -- if
    # either inset grows much *larger* (feature moves farther from this
    # corner, toward the plate's center), re-check that both stay fully
    # inside SC_X0/SC_Y1 below; a smaller inset only pulls a feature
    # closer to the corner, deeper inside the window, not out of it.
    STACK_COUPON = OUT_DIR / f"{stem}_stack_coupon.stl"
    SC_X0, SC_Y0, SC_Y1 = geom.plate_x - 46.0, 0.0, 20.0
    stack_coupon = trimesh.boolean.intersection(
        [solid, bx(SC_X0, SC_Y0, -1, geom.plate_x, SC_Y1, geom.plate_z + geom.stack_h + 1)],
        engine="manifold",
    )
    _export_stl(
        stack_coupon, STACK_COUPON,
        f"Jig plate {VERSION} | {tag}"
        f"stack coupon {geom.plate_x - SC_X0:g}x{SC_Y1 - SC_Y0:g}"
        f"x{geom.plate_z + geom.stack_h:.1f}mm | "
        # "corner, " is dropped with a printer so the longest name still
        # fits the 80-byte header without cutting the tail off
        + ("magnet+rib wall test" if tag else "corner, magnet+rib wall test"),
    )
    print("wrote", STACK_COUPON)
    failed = [
        name for name, mesh in (("plate", solid), ("stack coupon", stack_coupon))
        if not mesh.is_watertight
    ]
    print(_mesh_summary("stack coupon", stack_coupon, 2, 2))

    IMG_DIR.mkdir(exist_ok=True)
    _plate_diagram(IMG_DIR / f"{stem}_diagram.png", geom)
    _tech_top_plan(IMG_DIR / f"{stem}_tech_top.png", geom)
    _tech_front_elevation(IMG_DIR / f"{stem}_tech_front.png", geom)
    _tech_detail(IMG_DIR / f"{stem}_tech_detail.png", geom)

    # the files above are still written so the broken mesh can be inspected,
    # but a non-watertight mesh must not pass for a good build
    if failed:
        print(
            f"error: {' and '.join(failed)} mesh not watertight -- the "
            "geometry is broken; do not release or print these STLs",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
