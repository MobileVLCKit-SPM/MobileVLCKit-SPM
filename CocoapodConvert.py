import hashlib
import inspect
import json
import lzma
import os
import re
import shutil
import tarfile
import traceback
import typing
import zipfile
from urllib.parse import urljoin, urlparse
from typing import Optional, Tuple, Union
import requests
from bs4 import BeautifulSoup
from github import Github, GitRelease, GitReleaseAsset, Repository, PaginatedList, Tag

from Shell import Shell
import logging
import functools

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def log_entry(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Entering {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"Exiting {func.__name__}")
        return result

    return wrapper


@log_entry
def json_load_str_safe(obj: dict, key: str, default_value: str) -> str:
    if key in obj:
        return obj[key]
    else:
        return default_value


class Configure:
    # def __init__(self):
    #     cfg_path = os.path.join(os.path.dirname(__file__), "configure.json")
    #     self.vlc_cocoapods_prod_url = "https://download.videolan.org/pub/cocoapods/prod/"
    #     self.github_file_store_url = ""
    #     self.github_tag_url = ""
    #     self.github_token = ""
    #     self.github_repo_name = ""
    #     self.github_owner_name = ""
    #     self.github_release_id = ""
    #     self.github_release_name = ""
    #     self.temp_path = "./temp"
    #     self.github_branch_name = "master"
    #     self.lipo_path = "lipo"
    #     self.cache_file_keep = "False"
    #     with open(cfg_path) as fp:
    #         self.cfg_json = json.load(fp)
    #     self.load_attributes()
    #     self.temp_path = os.path.abspath(self.temp_path)
    #     self.cache_file_keep = self.cache_file_keep.lower().strip() == "true"
    def __init__(self):
        self.vlc_cocoapods_prod_url = os.environ.get(
            "VLC_COCOAPODS_URL", "https://download.videolan.org/pub/cocoapods/prod/"
        )
        self.github_token = os.environ.get("GH_TOKEN")
        github_repository = os.environ.get("GITHUB_REPOSITORY")
        if github_repository:
            repo_parts = github_repository.split("/")

            self.github_owner_name = repo_parts[0]
            self.github_repo_name = repo_parts[1]
        else:
            self.github_owner_name = ""
            self.github_repo_name = ""
        self.github_release_id = ""
        self.github_release_name = "FileStorage"
        self.temp_path = os.environ.get("TEMP_PATH", "./temp")
        self.github_branch_name = os.environ.get("GITHUB_BRANCH", "master")
        self.lipo_path = os.environ.get("LIPO_PATH", "lipo")
        self.cache_file_keep = os.environ.get("CACHE_FILE_KEEP", "False")

    def load_attributes(self):
        attributes = inspect.getmembers(self, lambda a: not (inspect.isroutine(a)))
        for attribute in attributes:
            if (
                len(attribute) == 2
                and isinstance(attribute[0], str)
                and not attribute[0].startswith("__")
                and isinstance(attribute[1], str)
            ):
                self.load_attribute(attribute[0])

    def load_attribute(self, property_name: str):
        if property_name in self.cfg_json:
            value = self.cfg_json[property_name]
            if isinstance(value, str):
                setattr(self, property_name, value)


@log_entry
def full_href(base: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    else:
        return urljoin(base, path)


@log_entry
def analyse_tags_links(
    html: str, base_url: str, regexp: re.Pattern[str]
) -> dict[str, str]:

    links: dict[str, str] = dict()
    soup = BeautifulSoup(html, "html.parser")
    tags = soup.find_all("a")
    for link in tags:
        href: str = f"{link.get("href")}"
        result: list = regexp.findall(href)
        if len(result) > 0:
            # full_name = result[0][0]
            version = result[0][1]
            href = full_href(base_url, href)
            print(f"full->{href}")
            links[version] = href
    return links


@log_entry
def get_mobile_vlc_kit_links(href: str) -> dict[str, str]:
    text: str = requests.get(href).text
    regexp = re.compile(
        r"(MobileVLCKit-(\d+\.\d+\.\d+)([^\w]([\d\w\-])*){0,1}\.((tar.xz)|(zip)))"
    )
    return analyse_tags_links(text, href, regexp)


@log_entry
def get_mobile_vlc_kit_releases_assets(
    config: Configure,
    github: Optional[Github],
    repo: Optional[Repository.Repository],
    release: Optional[GitRelease.GitRelease],
) -> tuple[
    dict[str, str],
    Optional[Github],
    Optional[Repository.Repository],
    Optional[GitRelease.GitRelease],
]:
    github, repo, release = setup_github_if_need(github, repo, release, config)
    result: dict[str, str] = dict()
    regexp = re.compile(r"MobileVLCKit-(\d+\.\d+\.\d+)\.xcframework\.zip")
    assets: PaginatedList.PaginatedList = release.get_assets()
    for idx in range(0, assets.totalCount):
        asset: GitReleaseAsset.GitReleaseAsset = assets[idx]
        # asset.browser_download_url
        name = asset.name
        if name is not None:
            reg_result: list = regexp.findall(name)
            if reg_result is not None and len(reg_result) > 0:
                version = reg_result[0]
                result[version] = asset.browser_download_url
        else:
            print(f"name=>{name}")
    return result, github, repo, release


@log_entry
def get_mobile_vlc_kit_tags(
    config: Configure,
    github: Optional[Github],
    repo: Optional[Repository.Repository],
) -> tuple[dict[str, str], Optional[Github], Optional[Repository.Repository]]:
    github, repo, _ = setup_github_if_need(github, repo, None, config)
    tags: PaginatedList.PaginatedList = repo.get_tags()
    result: dict[str, str] = dict()
    for idx in range(0, tags.totalCount):
        tag: Tag.Tag = tags[idx]
        version = tag.name
        result[version] = tag.zipball_url
    return result, github, repo


@log_entry
def mkdirs(path: str):
    if not os.path.exists(path):
        mkdirs(os.path.dirname(path))
        os.mkdir(path)


@log_entry
def temp_do(do_func: typing.Callable[[str], bool], path: str, label: str) -> bool:
    if os.path.exists(path):
        print(f"{label} target path is exists")
        return True
    temp = f"{path}_temp"
    result = False
    try:
        if os.path.exists(temp):
            if os.path.isdir(temp):
                shutil.rmtree(temp)
            else:
                os.unlink(temp)
        mkdirs(os.path.dirname(temp))
        print(f"{label} will start")
        result = do_func(temp)
        print(f"{label} done")
    except Exception as e:
        print(f"{label} exception {e}")
        traceback.print_exc()
    if result:
        print(f"{label} success")
        os.rename(temp, path)
    elif os.path.exists(temp):
        print(f"{label} fail")
        if os.path.isdir(temp):
            shutil.rmtree(temp)
        else:
            os.unlink(temp)
    return result


@log_entry
def download_file(url: str, local_filename: str):
    if os.path.exists(local_filename):
        print(f"try download {url} file exists using cache")
        return True

    def _download(temp: str) -> bool:
        response = requests.get(url, stream=True)
        t = int(response.headers.get("content-length", 0))
        block_size = 1024 * 1024  # 1 M bit
        with open(temp, "wb") as file:
            for data in response.iter_content(block_size):
                file.write(data)
        if os.path.getsize(temp) == t:
            return True
        return False

    return temp_do(_download, local_filename, f"download {url}")


@log_entry
def untar(src_file: str, dest_path: str, target_name: str, mode: str = "r"):
    # base_name = os.path.basename(src_file)
    def _untar(temp_path: str) -> bool:
        found = False
        with tarfile.open(src_file, mode) as input_fp:
            for member in input_fp.getmembers():
                if (
                    member.name.endswith(target_name)
                    or member.path.find(target_name) >= 0
                ):
                    mkdirs(temp_path)
                    input_fp.extract(member, temp_path)
                    found = True
                # else:
                #     print(f'{base_name}-> {member.path}:{member.name}')
        return found

    temp_do(_untar, dest_path, f"untar {src_file}")


@log_entry
def unzip(src_file: str, dest_path: str, target_name: str):
    def _unzip(temp_path: str) -> bool:
        # unzip_dir_temp = f"{unzip_dir}_temp"
        # if os.path.exists(unzip_dir_temp):
        #     shutil.rmtree(unzip_dir_temp)
        # input_fp = zipfile.ZipFile(path)
        # input_fp.extractall(unzip_dir_temp)
        # os.rename(unzip_dir_temp, unzip_dir)
        input_fp = zipfile.ZipFile(src_file)
        found = False
        for member in input_fp.infolist():
            if member.filename.find(target_name) >= 0:
                mkdirs(temp_path)
                input_fp.extract(member, temp_path)
                found = True
            # else:
            #     print(member.filename)
        input_fp.close()
        return found

    temp_do(_unzip, dest_path, f"unzip {src_file}")


@log_entry
def unxz(src_file: str, dest_path: str):
    def _unxz(temp_path: str) -> bool:
        with lzma.open(src_file, "rb") as input_fp:
            with open(temp_path, "wb") as output_fp:
                shutil.copyfileobj(input_fp, output_fp)
                return True
        return False

    return temp_do(_unxz, dest_path, f"unxz {src_file}")


@log_entry
def convert_framework_to_xcframework(
    framework: str, xcframework: str, configure: Configure
) -> bool:
    mkdirs(xcframework)
    system_path = os.getenv("PATH")
    if len(configure.lipo_path) == 0:
        return False
    full_path = configure.lipo_path
    if not os.path.exists(configure.lipo_path):
        for path in system_path.split(":"):
            full_path = os.path.join(path, configure.lipo_path)
            if os.path.exists(full_path):
                configure.lipo_path = full_path

    if os.path.exists(full_path):
        framework_name = os.path.basename(framework)
        # framework_binary_name = os.path.splitext(framework_name)[0]
        binary_archives: list[str] = lipo_info(framework, full_path)
        parts: list[(list[str], bool)] = []
        simulator_architecture = ["arm64", "i386", "x86_64"]
        devices_architecture = ["arm64", "armv7", "armv7s"]
        if len(binary_archives) > 0:
            pick_architecture(binary_archives, devices_architecture, False, parts)
            pick_architecture(binary_archives, simulator_architecture, True, parts)
            info_plist = os.path.join(xcframework, "Info.plist")
            architecture_parts: list[(str, list[str])] = generate_info_plist(
                parts, info_plist, framework_name
            )
            for part in architecture_parts:
                name, infos = part
                generate_frameworks(
                    framework, os.path.join(xcframework, name), infos, full_path
                )
    return False


@log_entry
def copy_file_or_dir(src: str, new_full: str):
    print(f"src={src}")
    if os.path.isdir(src):
        shutil.copytree(src, new_full)
    else:
        shutil.copyfile(src, new_full)


@log_entry
def generate_frameworks(
    framework: str, xcframework: str, architectures: list[str], lipo_path: str
) -> bool:
    framework_name = os.path.basename(framework)
    framework_binary_name = os.path.splitext(framework_name)[0]
    framework_binary_path = os.path.join(framework, framework_binary_name)
    new_framework_path = os.path.join(xcframework, framework_name)
    new_framework_binary_path = os.path.join(new_framework_path, framework_binary_name)
    mkdirs(new_framework_path)
    if len(architectures) > 1:
        architecture_temp_path_list: list[str] = []
        architecture_temp_path_raw_list = []
        for architecture in architectures:
            architecture_temp_path = f"{framework_binary_path}_{architecture}"
            shell = Shell(
                f'{lipo_path} -thin {architecture} "{framework_binary_path}" -output "{architecture_temp_path}"'
            )
            shell.run()
            if shell.ret_code != 0:
                return False
            architecture_temp_path_list.append(f'"{architecture_temp_path}"')
            architecture_temp_path_raw_list.append(architecture_temp_path)
        temps = " ".join(architecture_temp_path_list)
        shell = Shell(
            f'{lipo_path} -create {temps} -output "{new_framework_binary_path}"'
        )
        shell.run()
        for path in architecture_temp_path_raw_list:
            os.unlink(path)

        if shell.ret_code != 0:
            return False
        # copy other files
        for name in os.listdir(framework):
            full = os.path.join(framework, name)
            new_full = os.path.join(new_framework_path, name)
            if not os.path.exists(new_full):
                copy_file_or_dir(full, new_full)
    else:
        copy_file_or_dir(framework, new_framework_path)
    return True


@log_entry
def pick_architecture(
    exists_architecture: list[str],
    want_architecture: list[str],
    platform: bool,
    add_to_target: list[(list[str], bool)],
) -> (list[str], bool):
    part: list[str] = []
    for name in want_architecture:
        if name in exists_architecture:
            part.append(name)
    if len(part) > 0:
        add_to_target.append((part, platform))
    return part, platform


@log_entry
def generate_info_plist(
    parts: list[(list[str], bool)], plist_path: str, framework_name: str
) -> list[(str, list[str])]:
    result: list[(str, list[str])] = []
    available_libraries: list[str] = []
    for part, isSimulator in parts:
        suff = ""
        addition_attribute = ""
        if isSimulator:
            suff = "-simulator"
            addition_attribute = """
            <key>SupportedPlatformVariant</key>
			<string>simulator</string>
            """
        library_identifier = f'ios-{"_".join(part)}{suff}'
        result.append((library_identifier, part))
        part_r2: list[str] = []
        for name in part:
            part_r2.append(f"                    <string>{name}</string>")
        supported_architectures = "\n".join(part_r2)

        available_librarie = f"""<dict>
                <key>LibraryIdentifier</key>
                <string>{library_identifier}</string>
                <key>LibraryPath</key>
                <string>{framework_name}</string>
                <key>SupportedArchitectures</key>
                <array>
                    {supported_architectures}
                </array>
                <key>SupportedPlatform</key>
                <string>ios</string>{addition_attribute}
            </dict>
        """
        available_libraries.append(available_librarie)
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
                    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
                    <plist version="1.0">
                    <dict>
                        <key>AvailableLibraries</key>
                        <array>
                            {"".join(available_libraries)}
                        </array>
                        <key>CFBundlePackageType</key>
                        <string>XFWK</string>
                        <key>XCFrameworkFormatVersion</key>
                        <string>1.0</string>
                    </dict>
                    </plist>
                    """
    with open(plist_path, "w") as fp:
        fp.write(plist_content)
    return result


@log_entry
def lipo_info(framework_path: str, lipo_path: str) -> list[str]:
    binary_archives: list[str] = []
    framework_name = os.path.splitext(os.path.basename(framework_path))[0]
    binary_path = os.path.join(framework_path, framework_name)
    shell = Shell(f'{lipo_path} -info "{binary_path}"')
    shell.run()
    if shell.ret_code == 0:
        # Architectures in the fat file: MobileVLCKit are: armv7 armv7s i386 x86_64 arm64
        # Non-fat file: MobileVLCKit_armv7 is architecture: armv7
        infos = shell.ret_info.decode("utf-8").strip()

        valid_architectures = ["armv7", "armv7s", "i386", "x86_64", "arm64"]
        if infos.startswith("Architectures in the fat file"):
            key = f" are:"
            idx = infos.find(key)
            if idx >= 0:
                architectures = infos[idx + len(key) :]
                architectures_comp = architectures.split(" ")
                for architecture in architectures_comp:
                    if architecture in valid_architectures:
                        binary_archives.append(architecture)
        elif infos.startswith("Non-fat file:"):
            key = "is architecture:"
            idx = infos.find(key)
            if idx >= 0:
                architecture_info = infos[idx + len(key) :].strip()
                if architecture_info in valid_architectures:
                    binary_archives.append(architecture_info)
    return binary_archives


@log_entry
def download_cocoapod_archive_file(url: str, temp_path: str):
    temp_path = os.path.join(temp_path, "cocoapods")
    mkdirs(temp_path)
    parser_result = urlparse(url)
    file_name = os.path.basename(parser_result.path)
    download_path = os.path.join(temp_path, file_name)
    if download_file(url, download_path):
        return download_path
    else:
        return None


@log_entry
def file_tree_search_first(base_path: str, target_name: str) -> Optional[str]:
    for path, dir_list, file_list in os.walk(base_path):
        for name in dir_list:
            if name == target_name:
                return os.path.join(path, name)
        for name in file_list:
            if name == target_name:
                return os.path.join(path, name)
    return None


@log_entry
def convert_new_release_assets(
    path: str,
    version: str,
    temp_path: str,
    need_framewrok_convert: bool,
    configure: Configure,
) -> Optional[str]:
    if path is None or version is None or temp_path is None:
        return None

    xcframework = "MobileVLCKit.xcframework"
    if need_framewrok_convert:
        xcframework = "MobileVLCKit.framework"
    temp_files: list[str] = []

    def cleanup():
        for rm_path in temp_files:
            if os.path.exists(rm_path):
                if os.path.isdir(rm_path):
                    shutil.rmtree(rm_path)
                else:
                    os.unlink(rm_path)

    unarchive_path = os.path.join(
        os.path.dirname(path), os.path.splitext(os.path.basename(path))[0]
    )
    if path.endswith(".tar.xz"):
        xz_dir = os.path.dirname(path)
        unarchive_path = os.path.join(
            xz_dir, os.path.splitext(os.path.splitext(os.path.basename(path))[0])[0]
        )
        if not os.path.exists(unarchive_path):
            temp_files.append(unarchive_path)
            untar(path, unarchive_path, xcframework, "r:xz")
    elif path.endswith(".zip"):
        if not os.path.exists(unarchive_path):
            temp_files.append(unarchive_path)
            unzip(path, unarchive_path, xcframework)

    mobile_vlc_kit_xcframework = file_tree_search_first(unarchive_path, xcframework)
    if mobile_vlc_kit_xcframework is None:
        cleanup()
        return None
    if need_framewrok_convert:
        mobile_vlc_kit_framework = mobile_vlc_kit_xcframework
        mobile_vlc_kit_xcframework = (
            f"{os.path.splitext(mobile_vlc_kit_xcframework)[0]}.xcframework"
        )
        convert_framework_to_xcframework(
            mobile_vlc_kit_framework, mobile_vlc_kit_xcframework, configure
        )

    xcframework_zip_dir = os.path.join(temp_path, "xcframework-zip")
    mkdirs(xcframework_zip_dir)
    xcframework_zip = os.path.join(
        xcframework_zip_dir, f"MobileVLCKit-{version}.xcframework.zip"
    )
    if zip_folder(mobile_vlc_kit_xcframework, xcframework_zip):
        return xcframework_zip
    else:
        return None


@log_entry
def zip_folder(folder_path: str, target_zip_path: str) -> bool:
    folder_name = os.path.basename(folder_path)

    def _zip(temp: str) -> bool:
        output_fp = zipfile.ZipFile(temp, "w")
        output_fp.write(folder_path, folder_name)
        for path, dir_list, file_list in os.walk(folder_path):
            sub_path = str(path)
            if sub_path.startswith(folder_path):
                sub_path = sub_path[len(folder_path) :]
            if sub_path.startswith("/"):
                sub_path = sub_path[1:]
            sub_path = f"{folder_name}/{sub_path}"
            for name in dir_list:
                full_path = os.path.join(path, name)
                zip_name_full = os.path.join(sub_path, name)
                output_fp.write(full_path, zip_name_full)
                print(f"path:{path} sub:{sub_path} zip:{zip_name_full}")
            for name in file_list:
                full_path = os.path.join(path, name)
                zip_name_full = os.path.join(sub_path, name)
                output_fp.write(full_path, zip_name_full)
                print(f"path:{path} sub:{sub_path} zip:{zip_name_full}")

        output_fp.close()
        return True

    return temp_do(_zip, target_zip_path, f"zip {os.path.basename(target_zip_path)}")


@log_entry
def setup_github_if_need(
    github: Optional[Github],
    repo: Optional[Repository.Repository],
    release: Optional[GitRelease.GitRelease],
    configure: Configure,
) -> tuple[
    Optional[Github], Optional[Repository.Repository], Optional[GitRelease.GitRelease]
]:

    if github is None:
        github = Github(configure.github_token)
    if repo is None:
        repo = github.get_repo(
            f"{configure.github_owner_name}/{configure.github_repo_name}"
        )
    if len(configure.github_release_id) == 0:
        if len(configure.github_release_name) == 0:
            print("github_release_id and github_release_name is null , fail")
            return github, repo, release
        releases = repo.get_releases()
        for release in releases:
            if release.tag_name == configure.github_release_name:
                configure.github_release_id = str(release.id)
                break

    release = repo.get_release(int(configure.github_release_id))
    return github, repo, release


@log_entry
def do_convert(
    version: str,
    file_url: str,
    configure: Configure,
    github: Optional[Github] = None,
    repo: Optional[Repository.Repository] = None,
    release: Optional[GitRelease.GitRelease] = None,
    need_framewrok_convert: bool = False,
) -> tuple[
    Optional[str],
    Optional[str],
    Optional[Github],
    Optional[Repository.Repository],
    Optional[GitRelease.GitRelease],
]:
    """
    将 vlc cocoapods 地址转换为 github release url 地址
    :param need_framewrok_convert:
    :param version:  版本
    :param file_url:  文件位置
    :param configure: 配置
    :param github:    github 对象复用
    :param repo:      github repo 对象复用
    :param release:   release 对象复用
    :return:  url,sha256,github,release
    """
    local_path = download_cocoapod_archive_file(file_url, configure.temp_path)
    release_path = convert_new_release_assets(
        local_path, version, configure.temp_path, need_framewrok_convert, configure
    )

    if release_path is None:
        return None, None, github, repo, release

    github, repo, release = setup_github_if_need(github, repo, release, configure)

    # sha256 = sha356(release_path)
    release_name = f"MobileVLCKit-{version}.xcframework.zip"
    print(f"upload file to release {release_path} ->{release_name}")
    asset: GitReleaseAsset = release.upload_asset(release_path, release_name)
    print(f"calculate file sha256 {release_path}")
    sha = file_sha256(release_path)
    print(f"calculate file sha256 {release_path} -> {sha}")
    if not configure.cache_file_keep:
        os.unlink(release_path)
    return asset.browser_download_url, sha, github, repo, release


@log_entry
def file_sha256(release_path: str):
    _256 = hashlib.sha256()
    current_position = 0
    last_print_position = 0
    with open(release_path, "rb") as fp:
        while True:
            block = fp.read(1024 * 1024)
            if block is None or len(block) == 0:
                break
            current_position += len(block)
            _256.update(block)
            if current_position - last_print_position > 1024 * 1024 * 500:
                print(f"calcuate sha256:{release_path} {current_position}")
                last_print_position = current_position
    sha = _256.hexdigest()
    return sha


@log_entry
def string_sha(url: str) -> str:
    _sha256 = hashlib.sha256()
    _sha256.update(url.encode("utf-8"))
    return _sha256.hexdigest()


@log_entry
def bytes_sha(data: bytes) -> str:
    _sha256 = hashlib.sha256()
    _sha256.update(data)
    return _sha256.hexdigest()


@log_entry
def add_tag(
    release_url: str,
    file_hash: str,
    version: str,
    configure: Configure,
    github: Github,
    repo: Repository,
) -> tuple[Github, Repository]:
    if repo is None:
        if github is None:
            github = Github(configure.github_token)

        repo = github.get_repo(
            f"{configure.github_owner_name}/{configure.github_repo_name}"
        )
    package_swift_path = "Package.swift"
    contents = repo.get_contents(package_swift_path, ref=configure.github_branch_name)
    # modify content
    # TODO: modify content
    url_exp = re.compile(r'url\s*:\s*"https://github.com/[^"]*.zip"\s*,')
    sha_exp = re.compile(r'checksum\s*:\s*"[\w\d]*"')
    package_swift = contents.decoded_content.decode("utf-8")
    package_swift = url_exp.sub(f'url:"{release_url}",', package_swift)
    package_swift = sha_exp.sub(f'checksum:"{file_hash}"', package_swift)

    package_swift_bytes = package_swift.encode("utf-8")
    # sha = bytes_sha(package_swift_bytes)
    with open("_update_package_swift.swift", "wb") as fp:
        fp.write(package_swift_bytes)

    git_message = f"add {version} url:{release_url} sha256:{file_hash}"
    update_release = repo.update_file(
        package_swift_path,
        git_message,
        package_swift,
        contents.sha,
        branch=configure.github_branch_name,
    )
    # {'commit': Commit(sha="b06e05400afd6baee13fff74e38553d135dca7dc"), 'content': ContentFile(path="test.txt")}

    commit: github.Commit.Commit = update_release["commit"]

    # :calls: `POST /repos/{owner}/{repo}/git/tags <http://docs.github.com/en/rest/reference/git#tags>`_
    # :param tag: string
    # :param message: string
    # :param object: string
    # :param type: string
    # :param tagger: :class:`github.InputGitAuthor.InputGitAuthor`
    # :rtype: :class:`github.GitTag.GitTag`

    print(
        f"create tag and release tag={version},tag_message={git_message},release_name={version},"
        f'release_message={git_message},object={commit.sha},type="commit"'
    )
    new_git_release: GitRelease.GitRelease = repo.create_git_tag_and_release(
        tag=version,
        tag_message=git_message,
        release_name=version,
        release_message=git_message,
        object=commit.sha,
        type="commit",
    )
    print(f"add tag:{new_git_release.raw_data} {new_git_release}")
    return github, repo


@log_entry
def cleanup_mini(configure: Configure):
    cocoapods = os.path.join(configure.temp_path, "cocoapods")
    if os.path.exists(cocoapods):
        for name in os.listdir(cocoapods):
            full = os.path.join(cocoapods, name)
            if os.path.isdir(full):
                shutil.rmtree(full)
            elif os.path.isfile(full) and name.endswith(".tar"):
                os.remove(full)
            elif not configure.cache_file_keep:
                os.unlink(full)


@log_entry
def version_to_long(version: str) -> int:
    version_long = 0
    comps = version.split(".")
    for comp in comps:
        version_long = version_long * 1000 + int(comp)
    return version_long


@log_entry
def get_release_hash(url: str, configure: Configure) -> str:
    download_path = os.path.join(configure.temp_path, string_sha(url))
    download_file(url, download_path)
    sha_value = file_sha256(download_path)
    if not configure.cache_file_keep:
        os.unlink(download_path)
    return sha_value


@log_entry
def do_main():
    configure = Configure()
    github: Optional[Github] = None
    git_release: Optional[GitRelease.GitRelease] = None
    git_repo: Optional[Repository.Repository] = None

    github_file_links, github, git_repo, git_release = (
        get_mobile_vlc_kit_releases_assets(configure, github, git_repo, git_release)
    )
    github_tags, github, git_repo = get_mobile_vlc_kit_tags(configure, github, git_repo)

    print(f'github_tags=>{json.dumps(github_tags,indent='\t')}')

    vlc_links: dict[str, str] = get_mobile_vlc_kit_links(
        configure.vlc_cocoapods_prod_url
    )
    convert_list: dict[str, str] = dict()
    for version in vlc_links.keys():
        href = vlc_links[version]
        if version not in github_tags:
            convert_list[version] = href

    for version in convert_list.keys():
        long_version = version_to_long(version)
        need_framewrok_convert = False
        if long_version <= 3006001:
            continue
        if long_version < 3003016:
            need_framewrok_convert = True

        # release_url: str = ""
        # file_hash: str = ""
        if version in github_file_links:
            release_url: str = github_file_links[version]
            file_hash: str = get_release_hash(release_url, configure)
        else:
            release_url, file_hash, g, repo, release = do_convert(
                version=version,
                file_url=convert_list[version],
                configure=configure,
                github=github,
                repo=git_repo,
                release=git_release,
                need_framewrok_convert=need_framewrok_convert,
            )
            github = g
            git_release = release
            git_repo = repo

        if release_url is not None and file_hash is not None:
            g, r = add_tag(
                release_url,
                file_hash,
                version,
                configure=configure,
                github=github,
                repo=git_repo,
            )
            github = g
            git_repo = r
        cleanup_mini(configure)


if __name__ == "__main__":
    do_main()
