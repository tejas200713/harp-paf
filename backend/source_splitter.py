"""C++ source splitter for HARP-PAF."""

from dataclasses import dataclass
from pathlib import Path
import re

import tree_sitter_cpp
from tree_sitter import Language, Parser


@dataclass
class SplitResult:
    original_file: str
    generated_files: list[str]
    success: bool
    message: str


CPP_LANGUAGE = Language(tree_sitter_cpp.language())
parser = Parser(CPP_LANGUAGE)


def _text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8")


def _function_name(source: bytes, node) -> str:
    declarator = node.child_by_field_name("declarator")
    if declarator is None:
        return ""
    curr = declarator
    while curr:
        if curr.type in ("identifier", "field_identifier", "qualified_identifier", "destructor_name"):
            return _text(source, curr)
        next_curr = curr.child_by_field_name("declarator")
        if next_curr:
            curr = next_curr
        else:
            found = False
            for child in curr.named_children:
                if child.type in (
                    "identifier", "field_identifier", "qualified_identifier",
                    "function_declarator", "pointer_declarator", "reference_declarator"
                ):
                    curr = child
                    found = True
                    break
            if not found:
                break
    return ""


def _function_info(source: bytes, node):
    """Extract a top-level function definition."""
    body = node.child_by_field_name("body")
    declarator = node.child_by_field_name("declarator")

    if body is None or declarator is None:
        raise ValueError("Unsupported C++ function declaration")

    name = _function_name(source, node)
    if not name:
        raise ValueError("Could not determine function name")

    raw_decl = source[node.start_byte:body.start_byte].decode("utf-8").strip() + ";"
    # If function had static storage class, strip static for the shared header forward declaration
    declaration = re.sub(r'^\s*static\s+', '', raw_decl)

    raw_def = _text(source, node)
    definition = re.sub(r'^\s*static\s+', '', raw_def)

    return name, declaration, definition


def split_source(source_path: Path, output_dir: Path) -> SplitResult:
    """Split C++ functions into separate translation units."""
    source_path = Path(source_path)
    output_dir = Path(output_dir)

    if source_path.suffix.lower() != ".cpp":
        raise ValueError("Only .cpp files are supported")

    raw = source_path.read_bytes()
    if not raw or len(raw) > 500 * 1024:
        raise ValueError("Source must be between 1 byte and 500 KB")

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Source must be UTF-8") from exc

    tree = parser.parse(raw)

    if tree.root_node.has_error:
        raise ValueError("C++ syntax parsing failed. Please check for syntax errors.")

    shared_preamble = []
    functions = []
    seen_names = set()

    for node in tree.root_node.named_children:
        if node.type in (
            "struct_specifier", "class_specifier", "enum_specifier", "union_specifier"
        ):
            snippet = _text(raw, node).strip()
            if not snippet.endswith(";"):
                snippet += ";"
            shared_preamble.append(snippet)

        elif node.type in (
            "preproc_include", "preproc_def", "preproc_function_def",
            "preproc_ifdef", "preproc_if", "preproc_else", "preproc_elif",
            "using_declaration", "type_definition",
            "template_declaration", "declaration", "namespace_definition"
        ):
            shared_preamble.append(_text(raw, node).strip())

        elif node.type == "function_definition":
            info = _function_info(raw, node)
            name = info[0]
            if name in seen_names and name != "main":
                count = sum(1 for f in functions if f[0] == name)
                info = (f"{name}_{count}", info[1], info[2])
            seen_names.add(name)
            functions.append(info)

        elif node.type == "comment":
            continue

        else:
            snippet = _text(raw, node).strip()
            if snippet:
                shared_preamble.append(snippet)

    main_functions = [f for f in functions if f[0] == "main"]
    helpers = [f for f in functions if f[0] != "main"]

    if len(main_functions) != 1:
        raise ValueError("Exactly one main() function is required")

    if len(helpers) < 1:
        raise ValueError("At least one helper function is required to split into multiple modules")

    output_dir.mkdir(parents=True, exist_ok=True)

    header_parts = ["#pragma once\n"]
    if shared_preamble:
        header_parts.append("\n".join(dict.fromkeys(shared_preamble)))
    if helpers:
        header_parts.append("\n// Forward declarations\n" + "\n".join(f[1] for f in helpers))

    header = "\n\n".join(header_parts) + "\n"

    generated = []

    header_path = output_dir / "generated.h"
    header_path.write_text(header, encoding="utf-8")
    generated.append(str(header_path))

    for index, function in enumerate(helpers, start=1):
        filename = f"module_{index:02d}.cpp"
        path = output_dir / filename
        path.write_text(
            '#include "generated.h"\n\n'
            + function[2] + "\n",
            encoding="utf-8",
        )
        generated.append(str(path))

    main_path = output_dir / "main.cpp"
    main_path.write_text(
        '#include "generated.h"\n\n'
        + main_functions[0][2] + "\n",
        encoding="utf-8",
    )
    generated.append(str(main_path))

    return SplitResult(
        original_file=str(source_path),
        generated_files=generated,
        success=True,
        message=f"Generated {len(helpers) + 1} C++ source files",
    )
