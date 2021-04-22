"Make the custom certificate and private key files used by test_ssl\nand friends."
import os
import pprint
import shutil
import tempfile
from subprocess import *

startdate = "20180829142316Z"
enddate = "20371028142316Z"
req_template = "\n    [ default ]\n    base_url               = http://testca.pythontest.net/testca\n\n    [req]\n    distinguished_name     = req_distinguished_name\n    prompt                 = no\n\n    [req_distinguished_name]\n    C                      = XY\n    L                      = Castle Anthrax\n    O                      = Python Software Foundation\n    CN                     = {hostname}\n\n    [req_x509_extensions_nosan]\n\n    [req_x509_extensions_simple]\n    subjectAltName         = @san\n\n    [req_x509_extensions_full]\n    subjectAltName         = @san\n    keyUsage               = critical,keyEncipherment,digitalSignature\n    extendedKeyUsage       = serverAuth,clientAuth\n    basicConstraints       = critical,CA:false\n    subjectKeyIdentifier   = hash\n    authorityKeyIdentifier = keyid:always,issuer:always\n    authorityInfoAccess    = @issuer_ocsp_info\n    crlDistributionPoints  = @crl_info\n\n    [ issuer_ocsp_info ]\n    caIssuers;URI.0        = $base_url/pycacert.cer\n    OCSP;URI.0             = $base_url/ocsp/\n\n    [ crl_info ]\n    URI.0                  = $base_url/revocation.crl\n\n    [san]\n    DNS.1 = {hostname}\n    {extra_san}\n\n    [dir_sect]\n    C                      = XY\n    L                      = Castle Anthrax\n    O                      = Python Software Foundation\n    CN                     = dirname example\n\n    [princ_name]\n    realm = EXP:0, GeneralString:KERBEROS.REALM\n    principal_name = EXP:1, SEQUENCE:principal_seq\n\n    [principal_seq]\n    name_type = EXP:0, INTEGER:1\n    name_string = EXP:1, SEQUENCE:principals\n\n    [principals]\n    princ1 = GeneralString:username\n\n    [ ca ]\n    default_ca      = CA_default\n\n    [ CA_default ]\n    dir = cadir\n    database  = $dir/index.txt\n    crlnumber = $dir/crl.txt\n    default_md = sha256\n    startdate = {startdate}\n    default_startdate = {startdate}\n    enddate = {enddate}\n    default_enddate = {enddate}\n    default_days = 7000\n    default_crl_days = 7000\n    certificate = pycacert.pem\n    private_key = pycakey.pem\n    serial    = $dir/serial\n    RANDFILE  = $dir/.rand\n    policy          = policy_match\n\n    [ policy_match ]\n    countryName             = match\n    stateOrProvinceName     = optional\n    organizationName        = match\n    organizationalUnitName  = optional\n    commonName              = supplied\n    emailAddress            = optional\n\n    [ policy_anything ]\n    countryName   = optional\n    stateOrProvinceName = optional\n    localityName    = optional\n    organizationName  = optional\n    organizationalUnitName  = optional\n    commonName    = supplied\n    emailAddress    = optional\n\n\n    [ v3_ca ]\n\n    subjectKeyIdentifier=hash\n    authorityKeyIdentifier=keyid:always,issuer\n    basicConstraints = CA:true\n\n    "
here = os.path.abspath(os.path.dirname(__file__))


def make_cert_key(
    hostname, sign=False, extra_san="", ext="req_x509_extensions_full", key="rsa:3072"
):
    print(("creating cert for " + hostname))
    tempnames = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tempnames.append(f.name)
    (req_file, cert_file, key_file) = tempnames
    try:
        req = req_template.format(
            hostname=hostname, extra_san=extra_san, startdate=startdate, enddate=enddate
        )
        with open(req_file, "w") as f:
            f.write(req)
        args = [
            "req",
            "-new",
            "-nodes",
            "-days",
            "7000",
            "-newkey",
            key,
            "-keyout",
            key_file,
            "-extensions",
            ext,
            "-config",
            req_file,
        ]
        if sign:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                tempnames.append(f.name)
                reqfile = f.name
            args += ["-out", reqfile]
        else:
            args += ["-x509", "-out", cert_file]
        check_call((["openssl"] + args))
        if sign:
            args = [
                "ca",
                "-config",
                req_file,
                "-extensions",
                ext,
                "-out",
                cert_file,
                "-outdir",
                "cadir",
                "-policy",
                "policy_anything",
                "-batch",
                "-infiles",
                reqfile,
            ]
            check_call((["openssl"] + args))
        with open(cert_file, "r") as f:
            cert = f.read()
        with open(key_file, "r") as f:
            key = f.read()
        return (cert, key)
    finally:
        for name in tempnames:
            os.remove(name)


TMP_CADIR = "cadir"


def unmake_ca():
    shutil.rmtree(TMP_CADIR)


def make_ca():
    os.mkdir(TMP_CADIR)
    with open(os.path.join("cadir", "index.txt"), "a+") as f:
        pass
    with open(os.path.join("cadir", "crl.txt"), "a+") as f:
        f.write("00")
    with open(os.path.join("cadir", "index.txt.attr"), "w+") as f:
        f.write("unique_subject = no")
    with open(os.path.join("cadir", "serial"), "w") as f:
        f.write("CB2D80995A69525B\n")
    with tempfile.NamedTemporaryFile("w") as t:
        req = req_template.format(
            hostname="our-ca-server", extra_san="", startdate=startdate, enddate=enddate
        )
        t.write(req)
        t.flush()
        with tempfile.NamedTemporaryFile() as f:
            args = [
                "req",
                "-config",
                t.name,
                "-new",
                "-nodes",
                "-newkey",
                "rsa:3072",
                "-keyout",
                "pycakey.pem",
                "-out",
                f.name,
                "-subj",
                "/C=XY/L=Castle Anthrax/O=Python Software Foundation CA/CN=our-ca-server",
            ]
            check_call((["openssl"] + args))
            args = [
                "ca",
                "-config",
                t.name,
                "-out",
                "pycacert.pem",
                "-batch",
                "-outdir",
                TMP_CADIR,
                "-keyfile",
                "pycakey.pem",
                "-selfsign",
                "-extensions",
                "v3_ca",
                "-infiles",
                f.name,
            ]
            check_call((["openssl"] + args))
            args = ["ca", "-config", t.name, "-gencrl", "-out", "revocation.crl"]
            check_call((["openssl"] + args))
    check_call(["openssl", "x509", "-in", "pycacert.pem", "-out", "capath/ceff1710.0"])
    shutil.copy("capath/ceff1710.0", "capath/b1930218.0")


def print_cert(path):
    import _ssl

    pprint.pprint(_ssl._test_decode_cert(path))


if __name__ == "__main__":
    os.chdir(here)
    (cert, key) = make_cert_key("localhost", ext="req_x509_extensions_simple")
    with open("ssl_cert.pem", "w") as f:
        f.write(cert)
    with open("ssl_key.pem", "w") as f:
        f.write(key)
    print("password protecting ssl_key.pem in ssl_key.passwd.pem")
    check_call(
        [
            "openssl",
            "pkey",
            "-in",
            "ssl_key.pem",
            "-out",
            "ssl_key.passwd.pem",
            "-aes256",
            "-passout",
            "pass:somepass",
        ]
    )
    check_call(
        [
            "openssl",
            "pkey",
            "-in",
            "ssl_key.pem",
            "-out",
            "keycert.passwd.pem",
            "-aes256",
            "-passout",
            "pass:somepass",
        ]
    )
    with open("keycert.pem", "w") as f:
        f.write(key)
        f.write(cert)
    with open("keycert.passwd.pem", "a+") as f:
        f.write(cert)
    make_ca()
    (cert, key) = make_cert_key("fakehostname", ext="req_x509_extensions_simple")
    with open("keycert2.pem", "w") as f:
        f.write(key)
        f.write(cert)
    (cert, key) = make_cert_key("localhost", sign=True)
    with open("keycert3.pem", "w") as f:
        f.write(key)
        f.write(cert)
    (cert, key) = make_cert_key("fakehostname", sign=True)
    with open("keycert4.pem", "w") as f:
        f.write(key)
        f.write(cert)
    (cert, key) = make_cert_key("localhost-ecc", sign=True, key="param:secp384r1.pem")
    with open("keycertecc.pem", "w") as f:
        f.write(key)
        f.write(cert)
    extra_san = [
        "otherName.1 = 1.2.3.4;UTF8:some other identifier",
        "otherName.2 = 1.3.6.1.5.2.2;SEQUENCE:princ_name",
        "email.1 = user@example.org",
        "DNS.2 = www.example.org",
        "dirName.1 = dir_sect",
        "URI.1 = https://www.python.org/",
        "IP.1 = 127.0.0.1",
        "IP.2 = ::1",
        "RID.1 = 1.2.3.4.5",
    ]
    (cert, key) = make_cert_key("allsans", sign=True, extra_san="\n".join(extra_san))
    with open("allsans.pem", "w") as f:
        f.write(key)
        f.write(cert)
    extra_san = [
        "DNS.2 = xn--knig-5qa.idn.pythontest.net",
        "DNS.3 = xn--knigsgsschen-lcb0w.idna2003.pythontest.net",
        "DNS.4 = xn--knigsgchen-b4a3dun.idna2008.pythontest.net",
        "DNS.5 = xn--nxasmq6b.idna2003.pythontest.net",
        "DNS.6 = xn--nxasmm1c.idna2008.pythontest.net",
    ]
    (cert, key) = make_cert_key("idnsans", sign=True, extra_san="\n".join(extra_san))
    with open("idnsans.pem", "w") as f:
        f.write(key)
        f.write(cert)
    (cert, key) = make_cert_key("nosan", sign=True, ext="req_x509_extensions_nosan")
    with open("nosan.pem", "w") as f:
        f.write(key)
        f.write(cert)
    unmake_ca()
    print("update Lib/test/test_ssl.py and Lib/test/test_asyncio/util.py")
    print_cert("keycert.pem")
    print_cert("keycert3.pem")
