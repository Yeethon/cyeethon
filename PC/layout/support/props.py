"\nProvides .props file.\n"
import os
from .constants import *

__all__ = ["get_props_layout"]
PYTHON_PROPS_NAME = "python.props"
PROPS_DATA = {
    "PYTHON_TAG": VER_DOT,
    "PYTHON_VERSION": os.getenv("PYTHON_NUSPEC_VERSION"),
    "PYTHON_PLATFORM": os.getenv("PYTHON_PROPS_PLATFORM"),
    "PYTHON_TARGET": "",
}
if not PROPS_DATA["PYTHON_VERSION"]:
    PROPS_DATA["PYTHON_VERSION"] = "{}.{}{}{}".format(
        VER_DOT, VER_MICRO, ("-" if VER_SUFFIX else ""), VER_SUFFIX
    )
PROPS_DATA["PYTHON_TARGET"] = "_GetPythonRuntimeFilesDependsOn{}{}_{}".format(
    VER_MAJOR, VER_MINOR, PROPS_DATA["PYTHON_PLATFORM"]
)
PROPS_TEMPLATE = '<?xml version="1.0" encoding="utf-8"?>\n<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">\n  <PropertyGroup Condition="$(Platform) == \'{PYTHON_PLATFORM}\'">\n    <PythonHome Condition="$(PythonHome) == \'\'">$([System.IO.Path]::GetFullPath("$(MSBuildThisFileDirectory)\\..\\..\\tools"))</PythonHome>\n    <PythonInclude>$(PythonHome)\\include</PythonInclude>\n    <PythonLibs>$(PythonHome)\\libs</PythonLibs>\n    <PythonTag>{PYTHON_TAG}</PythonTag>\n    <PythonVersion>{PYTHON_VERSION}</PythonVersion>\n\n    <IncludePythonExe Condition="$(IncludePythonExe) == \'\'">true</IncludePythonExe>\n    <IncludeDistutils Condition="$(IncludeDistutils) == \'\'">false</IncludeDistutils>\n    <IncludeLib2To3 Condition="$(IncludeLib2To3) == \'\'">false</IncludeLib2To3>\n    <IncludeVEnv Condition="$(IncludeVEnv) == \'\'">false</IncludeVEnv>\n\n    <GetPythonRuntimeFilesDependsOn>{PYTHON_TARGET};$(GetPythonRuntimeFilesDependsOn)</GetPythonRuntimeFilesDependsOn>\n  </PropertyGroup>\n\n  <ItemDefinitionGroup Condition="$(Platform) == \'{PYTHON_PLATFORM}\'">\n    <ClCompile>\n      <AdditionalIncludeDirectories>$(PythonInclude);%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>\n      <RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>\n    </ClCompile>\n    <Link>\n      <AdditionalLibraryDirectories>$(PythonLibs);%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>\n    </Link>\n  </ItemDefinitionGroup>\n\n  <Target Name="GetPythonRuntimeFiles" Returns="@(PythonRuntime)" DependsOnTargets="$(GetPythonRuntimeFilesDependsOn)" />\n\n  <Target Name="{PYTHON_TARGET}" Returns="@(PythonRuntime)">\n    <ItemGroup>\n      <_PythonRuntimeExe Include="$(PythonHome)\\python*.dll" />\n      <_PythonRuntimeExe Include="$(PythonHome)\\python*.exe" Condition="$(IncludePythonExe) == \'true\'" />\n      <_PythonRuntimeExe>\n        <Link>%(Filename)%(Extension)</Link>\n      </_PythonRuntimeExe>\n      <_PythonRuntimeDlls Include="$(PythonHome)\\DLLs\\*.pyd" />\n      <_PythonRuntimeDlls Include="$(PythonHome)\\DLLs\\*.dll" />\n      <_PythonRuntimeDlls>\n        <Link>DLLs\\%(Filename)%(Extension)</Link>\n      </_PythonRuntimeDlls>\n      <_PythonRuntimeLib Include="$(PythonHome)\\Lib\\**\\*" Exclude="$(PythonHome)\\Lib\\**\\*.pyc;$(PythonHome)\\Lib\\site-packages\\**\\*" />\n      <_PythonRuntimeLib Remove="$(PythonHome)\\Lib\\distutils\\**\\*" Condition="$(IncludeDistutils) != \'true\'" />\n      <_PythonRuntimeLib Remove="$(PythonHome)\\Lib\\lib2to3\\**\\*" Condition="$(IncludeLib2To3) != \'true\'" />\n      <_PythonRuntimeLib Remove="$(PythonHome)\\Lib\\ensurepip\\**\\*" Condition="$(IncludeVEnv) != \'true\'" />\n      <_PythonRuntimeLib Remove="$(PythonHome)\\Lib\\venv\\**\\*" Condition="$(IncludeVEnv) != \'true\'" />\n      <_PythonRuntimeLib>\n        <Link>Lib\\%(RecursiveDir)%(Filename)%(Extension)</Link>\n      </_PythonRuntimeLib>\n      <PythonRuntime Include="@(_PythonRuntimeExe);@(_PythonRuntimeDlls);@(_PythonRuntimeLib)" />\n    </ItemGroup>\n\n    <Message Importance="low" Text="Collected Python runtime from $(PythonHome):%0D%0A@(PythonRuntime->\'  %(Link)\',\'%0D%0A\')" />\n  </Target>\n</Project>\n'


def get_props_layout(ns):
    if ns.include_all or ns.include_props:
        d = dict(PROPS_DATA)
        if not d.get("PYTHON_PLATFORM"):
            d["PYTHON_PLATFORM"] = {
                "win32": "Win32",
                "amd64": "X64",
                "arm32": "ARM",
                "arm64": "ARM64",
            }[ns.arch]
        props = PROPS_TEMPLATE.format_map(d)
        (yield ("python.props", ("python.props", props.encode("utf-8"))))
