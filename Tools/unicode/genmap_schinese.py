import os
import re
from genmap_support import *

GB2312_C1 = (33, 126)
GB2312_C2 = (33, 126)
GBKL1_C1 = (129, 168)
GBKL1_C2 = (64, 254)
GBKL2_C1 = (169, 254)
GBKL2_C2 = (64, 160)
GB18030EXTP1_C1 = (161, 169)
GB18030EXTP1_C2 = (64, 254)
GB18030EXTP2_C1 = (170, 175)
GB18030EXTP2_C2 = (161, 254)
GB18030EXTP3_C1 = (215, 215)
GB18030EXTP3_C2 = (250, 254)
GB18030EXTP4_C1 = (248, 253)
GB18030EXTP4_C2 = (161, 254)
GB18030EXTP5_C1 = (254, 254)
GB18030EXTP5_C2 = (80, 254)
MAPPINGS_GB2312 = "http://people.freebsd.org/~perky/i18n/GB2312.TXT"
MAPPINGS_CP936 = (
    "http://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WINDOWS/CP936.TXT"
)
MAPPINGS_GB18030 = (
    "http://oss.software.ibm.com/cvs/icu/~checkout~/charset/data/xml/gb-18030-2000.xml"
)
re_gb18030ass = re.compile('<a u="([A-F0-9]{4})" b="([0-9A-F ]+)"/>')


def parse_gb18030map(fo):
    (m, gbuni) = ({}, {})
    for i in range(65536):
        if (i < 55296) or (i > 57343):
            gbuni[i] = None
    for (uni, native) in re_gb18030ass.findall(fo.read()):
        uni = eval(("0x" + uni))
        native = [eval(("0x" + u)) for u in native.split()]
        if len(native) <= 2:
            del gbuni[uni]
        if len(native) == 2:
            m.setdefault(native[0], {})
            m[native[0]][native[1]] = uni
    gbuni = [k for k in gbuni.keys()]
    gbuni.sort()
    return (m, gbuni)


def main():
    print("Loading Mapping File...")
    gb2312map = open_mapping_file("python-mappings/GB2312.TXT", MAPPINGS_GB2312)
    cp936map = open_mapping_file("python-mappings/CP936.TXT", MAPPINGS_CP936)
    gb18030map = open_mapping_file(
        "python-mappings/gb-18030-2000.xml", MAPPINGS_GB18030
    )
    (gb18030decmap, gb18030unilinear) = parse_gb18030map(gb18030map)
    gbkdecmap = loadmap(cp936map)
    gb2312decmap = loadmap(gb2312map)
    difmap = {}
    for (c1, m) in gbkdecmap.items():
        for (c2, code) in m.items():
            del gb18030decmap[c1][c2]
            if not gb18030decmap[c1]:
                del gb18030decmap[c1]
    for (c1, m) in gb2312decmap.items():
        for (c2, code) in m.items():
            (gbkc1, gbkc2) = ((c1 | 128), (c2 | 128))
            if gbkdecmap[gbkc1][gbkc2] == code:
                del gbkdecmap[gbkc1][gbkc2]
                if not gbkdecmap[gbkc1]:
                    del gbkdecmap[gbkc1]
    (gb2312_gbkencmap, gb18030encmap) = ({}, {})
    for (c1, m) in gbkdecmap.items():
        for (c2, code) in m.items():
            gb2312_gbkencmap.setdefault((code >> 8), {})
            gb2312_gbkencmap[(code >> 8)][(code & 255)] = (c1 << 8) | c2
    for (c1, m) in gb2312decmap.items():
        for (c2, code) in m.items():
            gb2312_gbkencmap.setdefault((code >> 8), {})
            gb2312_gbkencmap[(code >> 8)][(code & 255)] = (c1 << 8) | c2
    for (c1, m) in gb18030decmap.items():
        for (c2, code) in m.items():
            gb18030encmap.setdefault((code >> 8), {})
            gb18030encmap[(code >> 8)][(code & 255)] = (c1 << 8) | c2
    with open("mappings_cn.h", "w") as fp:
        print_autogen(fp, os.path.basename(__file__))
        print("Generating GB2312 decode map...")
        writer = DecodeMapWriter(fp, "gb2312", gb2312decmap)
        writer.update_decode_map(GB2312_C1, GB2312_C2)
        writer.generate()
        print("Generating GBK decode map...")
        writer = DecodeMapWriter(fp, "gbkext", gbkdecmap)
        writer.update_decode_map(GBKL1_C1, GBKL1_C2)
        writer.update_decode_map(GBKL2_C1, GBKL2_C2)
        writer.generate()
        print("Generating GB2312 && GBK encode map...")
        writer = EncodeMapWriter(fp, "gbcommon", gb2312_gbkencmap)
        writer.generate()
        print("Generating GB18030 extension decode map...")
        writer = DecodeMapWriter(fp, "gb18030ext", gb18030decmap)
        for i in range(1, 6):
            writer.update_decode_map(
                eval(("GB18030EXTP%d_C1" % i)), eval(("GB18030EXTP%d_C2" % i))
            )
        writer.generate()
        print("Generating GB18030 extension encode map...")
        writer = EncodeMapWriter(fp, "gb18030ext", gb18030encmap)
        writer.generate()
        print("Generating GB18030 Unicode BMP Mapping Ranges...")
        ranges = [[(-1), (-1), (-1)]]
        gblinnum = 0
        fp.write(
            "\nstatic const struct _gb18030_to_unibmp_ranges {\n    Py_UCS4   first, last;\n    DBCHAR       base;\n} gb18030_to_unibmp_ranges[] = {\n"
        )
        for uni in gb18030unilinear:
            if uni == (ranges[(-1)][1] + 1):
                ranges[(-1)][1] = uni
            else:
                ranges.append([uni, uni, gblinnum])
            gblinnum += 1
        filler = BufferedFiller()
        for (first, last, base) in ranges[1:]:
            filler.write("{", str(first), ",", str(last), ",", str(base), "},")
        filler.write(
            "{",
            "0,",
            "0,",
            str((((ranges[(-1)][2] + ranges[(-1)][1]) - ranges[(-1)][0]) + 1)),
            "}",
            "};",
        )
        filler.printout(fp)
    print("Done!")


if __name__ == "__main__":
    main()
