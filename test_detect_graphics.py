"""Regression checks for the GPU parsing in hardware_detector.detect_graphics.

Plain asserts, no pytest: this repo ships to a USB stick and its requirements are deliberately
just requests + tqdm. There is no CI here either, so this is a check you RUN, not one that runs
itself:

    python3 test_detect_graphics.py        # exits 0 on success, prints failures otherwise

Every lspci line below is a real one taken from the production database (the distinct set across
all scanned machines), which is where the two defects were found.
"""

import re
import sys

from hardware_detector import HardwareDetector

_LINE = re.compile(r'(?:VGA compatible controller|3D controller):\s*(.+?)(?:\s*\(rev.*\))?$')


def parse(gpu_line):
    """The classification half of detect_graphics, minus the lspci call and raw_data writes."""
    low = gpu_line.lower()
    match = _LINE.search(gpu_line)
    if not match:
        return None, None
    text = match.group(1).strip()
    bracket = HardwareDetector.model_bracket(text)

    if 'intel' in low:
        return (f"Intel {bracket}" if bracket else text), None
    if 'amd' in low and 'radeon' in low and not HardwareDetector.is_amd_discrete(low):
        return (f"AMD {bracket}" if bracket else text), None
    if 'nvidia' in low:
        return None, (f"NVIDIA {bracket}" if bracket else text)
    if 'amd' in low and HardwareDetector.is_amd_discrete(low):
        return None, (f"AMD {bracket}" if bracket else text)
    return None, None


# (real lspci line, expected integrated, expected dedicated)
CASES = [
    # --- AMD: two bracket groups, which is what broke -------------------------------------
    # APUs. "Radeon RX Vega 6" must NOT read as a discrete card.
    ("06:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Renoir "
     "[Radeon RX Vega 6 (Ryzen 4000/5000 Mobile Series)] (rev d3)",
     "AMD Radeon RX Vega 6 (Ryzen 4000/5000 Mobile Series)", None),
    ("05:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Cezanne "
     "[Radeon Vega Series / Radeon Vega Mobile Series] (rev c5)",
     "AMD Radeon Vega Series / Radeon Vega Mobile Series", None),
    ("04:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] "
     "Picasso/Raven 2 [Radeon Vega Series / Radeon Vega Mobile Series] (rev c2)",
     "AMD Radeon Vega Series / Radeon Vega Mobile Series", None),
    # R-series APUs carry no "rx" at all and were dropped entirely by the old "vega" gate.
    ("00:01.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Stoney "
     "[Radeon R2/R3/R4/R5 Graphics] (rev e2)",
     "AMD Radeon R2/R3/R4/R5 Graphics", None),
    ("00:01.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Wani "
     "[Radeon R5/R6/R7 Graphics] (rev c8)",
     "AMD Radeon R5/R6/R7 Graphics", None),
    # the one genuinely discrete AMD card in the catalog
    ("01:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Ellesmere "
     "[Radeon RX 470/480/570/570X/580/580X/590] (rev e7)",
     None, "AMD Radeon RX 470/480/570/570X/580/580X/590"),
    # --- single-bracket lines: last IS first, so nothing changes --------------------------
    ("00:02.0 VGA compatible controller: Intel Corporation CoffeeLake-H GT2 "
     "[UHD Graphics 630] (rev 3e)", "Intel UHD Graphics 630", None),
    ("01:00.0 3D controller: NVIDIA Corporation GP108M [GeForce MX150] (rev a1)",
     None, "NVIDIA GeForce MX150"),
    ("01:00.0 3D controller: NVIDIA Corporation TU117GLM [Quadro T1000 Mobile] (rev a1)",
     None, "NVIDIA Quadro T1000 Mobile"),
    # --- no bracket at all: fall back to the device text ---------------------------------
    ("00:02.0 VGA compatible controller: Intel Corporation Haswell-ULT Integrated "
     "Graphics Controller (rev 0b)",
     "Intel Corporation Haswell-ULT Integrated Graphics Controller", None),
    # not a GPU: the AMD sensor hub shares the vendor string and must be ignored
    ("00:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD] "
     "Raven/Raven2/Renoir Non-Sensor Fusion Hub KMDF driver", None, None),
]


def main():
    failures = []

    for line, want_integrated, want_dedicated in CASES:
        got = parse(line)
        if got != (want_integrated, want_dedicated):
            failures.append(
                f"  {line.split(':', 2)[-1].strip()[:70]}\n"
                f"     want int={want_integrated!r} ded={want_dedicated!r}\n"
                f"     got  int={got[0]!r} ded={got[1]!r}"
            )

    # the vendor alias must never end up as the model name
    for line, integrated, dedicated in CASES:
        for value in parse(line):
            if value and "AMD/ATI" in value:
                failures.append(f"  vendor alias leaked as a GPU name: {value!r}")

    # an APU is never both
    for line, _, _ in CASES:
        integrated, dedicated = parse(line)
        if integrated and dedicated:
            failures.append(f"  one line filled BOTH columns: {integrated!r} / {dedicated!r}")

    if failures:
        print(f"FAILED {len(failures)} check(s):\n" + "\n".join(failures))
        return 1
    print(f"ok — {len(CASES)} real lspci lines classified correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
