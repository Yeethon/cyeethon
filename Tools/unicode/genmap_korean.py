import os
from genmap_support import *

KSX1001_C1 = (33, 126)
KSX1001_C2 = (33, 126)
UHCL1_C1 = (129, 160)
UHCL1_C2 = (65, 254)
UHCL2_C1 = (161, 254)
UHCL2_C2 = (65, 160)
MAPPINGS_CP949 = (
    "http://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WINDOWS/CP949.TXT"
)


def main():
    mapfile = open_mapping_file("python-mappings/CP949.TXT", MAPPINGS_CP949)
    print("Loading Mapping File...")
    decmap = loadmap(mapfile)
    (uhcdecmap, ksx1001decmap, cp949encmap) = ({}, {}, {})
    for (c1, c2map) in decmap.items():
        for (c2, code) in c2map.items():
            if (c1 >= 161) and (c2 >= 161):
                ksx1001decmap.setdefault((c1 & 127), {})
                ksx1001decmap[(c1 & 127)][(c2 & 127)] = c2map[c2]
                cp949encmap.setdefault((code >> 8), {})
                cp949encmap[(code >> 8)][(code & 255)] = ((c1 << 8) | c2) & 32639
            else:
                uhcdecmap.setdefault(c1, {})
                uhcdecmap[c1][c2] = c2map[c2]
                cp949encmap.setdefault((code >> 8), {})
                cp949encmap[(code >> 8)][(code & 255)] = (c1 << 8) | c2
    with open("mappings_kr.h", "w") as fp:
        print_autogen(fp, os.path.basename(__file__))
        print("Generating KS X 1001 decode map...")
        writer = DecodeMapWriter(fp, "ksx1001", ksx1001decmap)
        writer.update_decode_map(KSX1001_C1, KSX1001_C2)
        writer.generate()
        print("Generating UHC decode map...")
        writer = DecodeMapWriter(fp, "cp949ext", uhcdecmap)
        writer.update_decode_map(UHCL1_C1, UHCL1_C2)
        writer.update_decode_map(UHCL2_C1, UHCL2_C2)
        writer.generate()
        print("Generating CP949 (includes KS X 1001) encode map...")
        writer = EncodeMapWriter(fp, "cp949", cp949encmap)
        writer.generate()
    print("Done!")


if __name__ == "__main__":
    main()
