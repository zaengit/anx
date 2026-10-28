"""Minimal Android binary XML manifest reader for ANX's APK subset."""
from __future__ import annotations

from dataclasses import dataclass
import struct


NO_INDEX = 0xFFFFFFFF
RES_XML_TYPE = 0x0003
RES_STRING_POOL_TYPE = 0x0001
RES_XML_START_ELEMENT_TYPE = 0x0102
RES_XML_END_ELEMENT_TYPE = 0x0103
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12
ANDROID_NS = "http://schemas.android.com/apk/res/android"
ACTION_MAIN = "android.intent.action.MAIN"
CATEGORY_LAUNCHER = "android.intent.category.LAUNCHER"


class ManifestError(ValueError):
    """The manifest is malformed or missing required metadata."""


@dataclass(frozen=True)
class ActivityInfo:
    name: str
    component_name: str
    alias_target: str | None = None

    @property
    def launch_class(self) -> str:
        return self.alias_target or self.name


@dataclass(frozen=True)
class ManifestInfo:
    package_name: str
    application_name: str | None
    activities: tuple[ActivityInfo, ...]
    launchers: tuple[ActivityInfo, ...]

    @property
    def launcher_activity(self) -> str | None:
        if len(self.launchers) != 1:
            return None
        return self.launchers[0].launch_class


def _u16(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ManifestError("unexpected end of binary XML")
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ManifestError("unexpected end of binary XML")
    return struct.unpack_from("<I", data, offset)[0]


def _length8(data: bytes, offset: int) -> tuple[int, int]:
    if offset < 0 or offset >= len(data):
        raise ManifestError("truncated UTF-8 string length")
    first = data[offset]
    offset += 1
    if first & 0x80:
        if offset >= len(data):
            raise ManifestError("truncated UTF-8 string length")
        return (((first & 0x7F) << 8) | data[offset], offset + 1)
    return first, offset


def _length16(data: bytes, offset: int) -> tuple[int, int]:
    first = _u16(data, offset)
    offset += 2
    if first & 0x8000:
        second = _u16(data, offset)
        return (((first & 0x7FFF) << 16) | second, offset + 2)
    return first, offset


def _parse_string_pool(data: bytes, offset: int, size: int, header_size: int) -> list[str]:
    if header_size < 28 or size < header_size:
        raise ManifestError("invalid string pool header")
    end = offset + size
    string_count = _u32(data, offset + 8)
    style_count = _u32(data, offset + 12)
    flags = _u32(data, offset + 16)
    strings_start = _u32(data, offset + 20)
    if string_count > 1_000_000 or style_count > 1_000_000:
        raise ManifestError("string pool count exceeds safety limit")
    offsets_start = offset + header_size
    strings_base = offset + strings_start
    offsets_end = offsets_start + 4 * (string_count + style_count)
    if offsets_end > end or strings_base > end:
        raise ManifestError("string pool offsets are out of bounds")
    if strings_base < offsets_end:
        raise ManifestError("string data overlaps string pool offsets")

    utf8 = bool(flags & 0x100)
    strings: list[str] = []
    for index in range(string_count):
        string_offset = _u32(data, offsets_start + 4 * index)
        cursor = strings_base + string_offset
        if cursor >= end:
            raise ManifestError("string offset is out of bounds")
        if utf8:
            _, cursor = _length8(data, cursor)  # UTF-16 code-unit length
            if cursor >= end:
                raise ManifestError("truncated UTF-8 string length")
            byte_length, cursor = _length8(data, cursor)
            string_end = cursor + byte_length
            if cursor > end or string_end >= end:
                raise ManifestError("truncated UTF-8 string")
            if data[string_end] != 0:
                raise ManifestError("unterminated UTF-8 string")
            try:
                strings.append(data[cursor:string_end].decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise ManifestError("invalid UTF-8 string in manifest") from exc
        else:
            if cursor + 2 > end:
                raise ManifestError("truncated UTF-16 string length")
            char_length, cursor = _length16(data, cursor)
            string_end = cursor + char_length * 2
            if cursor > end or string_end + 2 > end:
                raise ManifestError("truncated UTF-16 string")
            if data[string_end:string_end + 2] != b"\x00\x00":
                raise ManifestError("unterminated UTF-16 string")
            try:
                strings.append(data[cursor:string_end].decode("utf-16le"))
            except UnicodeDecodeError as exc:
                raise ManifestError("invalid UTF-16 string in manifest") from exc
    return strings


def _string(strings: list[str], index: int) -> str | None:
    if index == NO_INDEX:
        return None
    if index >= len(strings):
        raise ManifestError("string index is out of bounds")
    return strings[index]


def _read_attribute(data: bytes, offset: int, strings: list[str]) -> tuple[str | None, str, object]:
    namespace_index = _u32(data, offset)
    name_index = _u32(data, offset + 4)
    raw_index = _u32(data, offset + 8)
    value_size = _u16(data, offset + 12)
    data_type = data[offset + 15]
    value_data = _u32(data, offset + 16)
    if value_size < 8:
        raise ManifestError("invalid typed value in manifest attribute")

    namespace = _string(strings, namespace_index)
    name = _string(strings, name_index)
    if name is None:
        raise ManifestError("manifest attribute has no name")
    raw_value = _string(strings, raw_index)
    if raw_value is not None:
        value: object = raw_value
    elif data_type == TYPE_STRING:
        value = _string(strings, value_data)
    elif data_type == TYPE_INT_DEC:
        value = value_data
    elif data_type == TYPE_INT_HEX:
        value = f"0x{value_data:x}"
    elif data_type == TYPE_INT_BOOLEAN:
        value = bool(value_data)
    else:
        value = value_data
    return namespace, name, value


def _android_attr(attrs: dict[tuple[str | None, str], object], name: str) -> object | None:
    return attrs.get((ANDROID_NS, name))


def _resolve_class(package_name: str, name: object | None) -> str | None:
    if not isinstance(name, str) or not name:
        return None
    if name.startswith("."):
        return package_name + name
    if "." not in name:
        return package_name + "." + name
    return name


def parse_binary_manifest(data: bytes) -> ManifestInfo:
    """Parse package, application, activities, and MAIN/LAUNCHER components."""
    if len(data) < 8:
        raise ManifestError("binary manifest is too short")
    if _u16(data, 0) != RES_XML_TYPE:
        raise ManifestError("AndroidManifest.xml is not Android binary XML")
    root_header_size = _u16(data, 2)
    total_size = _u32(data, 4)
    if root_header_size < 8 or total_size != len(data):
        raise ManifestError("invalid binary XML root size")

    strings: list[str] | None = None
    package_name: str | None = None
    application_name: str | None = None
    activities: list[ActivityInfo] = []
    launchers: list[ActivityInfo] = []
    stack: list[dict[str, object]] = []
    offset = root_header_size

    while offset < total_size:
        if offset + 8 > total_size:
            raise ManifestError("truncated XML chunk header")
        chunk_type = _u16(data, offset)
        header_size = _u16(data, offset + 2)
        chunk_size = _u32(data, offset + 4)
        if header_size < 8 or chunk_size < header_size or offset + chunk_size > total_size:
            raise ManifestError("invalid XML chunk bounds")

        if chunk_type == RES_STRING_POOL_TYPE:
            if strings is not None:
                raise ManifestError("duplicate string pool")
            strings = _parse_string_pool(data, offset, chunk_size, header_size)
        elif chunk_type == RES_XML_START_ELEMENT_TYPE:
            if strings is None:
                raise ManifestError("start element appears before string pool")
            if header_size < 16:
                raise ManifestError("truncated start-element header")
            extension = offset + header_size
            if chunk_size < header_size + 20:
                raise ManifestError("truncated start-element chunk")
            name_index = _u32(data, extension + 4)
            tag = _string(strings, name_index)
            if tag is None:
                raise ManifestError("start element has no name")
            attribute_start = _u16(data, extension + 8)
            attribute_size = _u16(data, extension + 10)
            attribute_count = _u16(data, extension + 12)
            if attribute_size < 20 or attribute_count > 65535:
                raise ManifestError("invalid start-element attributes")
            attributes_offset = extension + attribute_start
            if attributes_offset + attribute_size * attribute_count > offset + chunk_size:
                raise ManifestError("start-element attributes are out of bounds")
            attrs: dict[tuple[str | None, str], object] = {}
            for index in range(attribute_count):
                namespace, name, value = _read_attribute(
                    data, attributes_offset + attribute_size * index, strings
                )
                attrs[(namespace, name)] = value

            if tag == "manifest":
                value = attrs.get((None, "package"))
                if isinstance(value, str):
                    package_name = value
            elif tag == "application":
                if package_name is None:
                    raise ManifestError("manifest package name is missing")
                application_name = _resolve_class(package_name, _android_attr(attrs, "name"))

            record: ActivityInfo | None = None
            if tag in ("activity", "activity-alias") and any(
                item.get("tag") == "application" for item in stack
            ):
                if package_name is None:
                    raise ManifestError("manifest package name is missing")
                name = _resolve_class(package_name, _android_attr(attrs, "name"))
                target = _resolve_class(package_name, _android_attr(attrs, "targetActivity"))
                if name is None:
                    raise ManifestError(f"<{tag}> is missing android:name")
                record = ActivityInfo(name=name, component_name=name, alias_target=target)

            frame: dict[str, object] = {"tag": tag, "record": record, "attrs": attrs}
            if tag == "intent-filter":
                parent_record = next((item.get("record") for item in reversed(stack)
                                      if item.get("record") is not None), None)
                frame["record"] = parent_record
                frame["has_main"] = False
                frame["has_launcher"] = False
            elif tag == "action":
                intent = next((item for item in reversed(stack)
                               if item.get("tag") == "intent-filter"), None)
                if intent is not None and attrs.get((ANDROID_NS, "name")) == ACTION_MAIN:
                    intent["has_main"] = True
            elif tag == "category":
                intent = next((item for item in reversed(stack)
                               if item.get("tag") == "intent-filter"), None)
                if intent is not None and attrs.get((ANDROID_NS, "name")) == CATEGORY_LAUNCHER:
                    intent["has_launcher"] = True
            stack.append(frame)

        elif chunk_type == RES_XML_END_ELEMENT_TYPE:
            if strings is None:
                raise ManifestError("end element appears before string pool")
            if header_size < 16 or chunk_size < header_size + 8:
                raise ManifestError("truncated end-element chunk")
            if not stack:
                raise ManifestError("unbalanced end element")
            name_index = _u32(data, offset + header_size + 4)
            tag = _string(strings, name_index)
            frame = stack.pop()
            if tag != frame.get("tag"):
                raise ManifestError("mismatched XML element tags")
            if tag == "intent-filter" and frame.get("has_main") and frame.get("has_launcher"):
                record = frame.get("record")
                if isinstance(record, ActivityInfo):
                    launchers.append(record)
            elif tag in ("activity", "activity-alias"):
                record = frame.get("record")
                if isinstance(record, ActivityInfo):
                    activities.append(record)
        offset += chunk_size

    if offset != total_size or strings is None:
        raise ManifestError("binary XML ended unexpectedly")
    if stack:
        raise ManifestError("unclosed XML elements")
    if package_name is None:
        raise ManifestError("manifest package name is missing")

    unique_launchers: list[ActivityInfo] = []
    seen_components: set[str] = set()
    for launcher in launchers:
        if launcher.component_name not in seen_components:
            unique_launchers.append(launcher)
            seen_components.add(launcher.component_name)
    return ManifestInfo(
        package_name=package_name,
        application_name=application_name,
        activities=tuple(activities),
        launchers=tuple(unique_launchers),
    )
