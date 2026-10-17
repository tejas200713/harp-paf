
"""Safe, limited C++ source splitter for HARP-PAF."""

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

ALLOWED_RETURNS = {"int", "void", "double", "float", "long", "bool"}
ALLOWED_TYPES = ALLOWED_RETURNS | {"char", "short", "unsigned"}


def _text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8")


def _function_info(source: bytes, node):
    """Extract a simple top-level function definition."""
    body = node.child_by_field_name("body")
    declarator = node.child_by_field_name("declarator")
    return_type = node.child_by_field_name("type")

    if body is None or declarator is None or return_type is None:
        raise ValueError("Unsupported C++ function declaration")

    if declarator.type != "function_declarator":
        raise ValueError("Only ordinary functions are supported")

    name_node = declarator.child_by_field_name("declarator")
    if name_node is None or name_node.type != "identifier":
        raise ValueError("Unsupported function name")

    name = _text(source, name_node)
    if not re.fullmatch(r"[A-Za-z_]\w*", name):
        raise ValueError("Invalid function name")

    if _text(source, return_type) not in ALLOWED_RETURNS:
        raise ValueError(f"Unsupported return type in {name}")

    params = declarator.child_by_field_name("parameters")
    if params is None:
        raise ValueError(f"Unsupported parameters in {name}")

    for child in params.named_children:
        if child.type == "variadic_parameter":
            raise ValueError(f"Variadic function not supported: {name}")
        if child.type != "parameter_declaration":
            raise ValueError(f"Unsupported parameter in {name}")

        param_type = child.child_by_field_name("type")
        param_name = child.child_by_field_name("declarator")

        if (
            param_type is None
            or _text(source, param_type) not in ALLOWED_TYPES
            or (
                param_name is not None
                and param_name.type != "identifier"
            )
        ):
            raise ValueError(f"Complex parameter in {name}")

    # Reject extra specifiers such as static, inline and templates.
    prefix = source[node.start_byte:return_type.start_byte].decode("utf-8")
    if prefix.strip():
        raise ValueError(f"Unsupported function specifier in {name}")

    definition = _text(source, node)
    declaration = source[
        node.start_byte:body.start_byte
    ].decode("utf-8").strip() + ";"

    if "=" in declaration or "..." in declaration:
        raise ValueError(f"Unsupported declaration in {name}")

    return name, declaration, definition


def split_source(source_path: Path, output_dir: Path) -> SplitResult:
    """Split supported C++ functions into separate translation units."""
    source_path = Path(source_path)
    output_dir = Path(output_dir)

    if source_path.suffix.lower() != ".cpp":
        raise ValueError("Only .cpp files are supported")

    raw = source_path.read_bytes()
    if not raw or len(raw) > 100 * 1024:
        raise ValueError("Source must be between 1 byte and 100 KB")

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Source must be UTF-8") from exc

    tree = parser.parse(raw)

    if tree.root_node.has_error:
        raise ValueError("C++ syntax parsing failed")

    includes = []
    functions = []
    names = set()

    for node in tree.root_node.named_children:
        if node.type == "preproc_include":
            directive = _text(raw, node).strip()
            if not re.fullmatch(
                r'#\s*include\s*<[\w./+-]+>', directive
            ):
                raise ValueError("Only standard header includes are supported")
            includes.append(directive)

        elif node.type == "function_definition":
            info = _function_info(raw, node)
            if info[0] in names:
                raise ValueError(f"Duplicate function: {info[0]}")
            names.add(info[0])
            functions.append(info)

        elif node.type == "comment":
            continue

        else:
            raise ValueError(
                f"Unsupported top-level construct: {node.type}"
            )

    main_functions = [f for f in functions if f[0] == "main"]
    helpers = [f for f in functions if f[0] != "main"]

    if len(main_functions) != 1:
        raise ValueError("Exactly one main() function is required")

    if len(helpers) < 2:
        raise ValueError("At least two helper functions are required")

    if len(functions) > 16:
        raise ValueError("Maximum 16 functions supported")

    # All validation above finishes before writing generated files.
    output_dir.mkdir(parents=True, exist_ok=True)

    header = (
        "#pragma once\n\n"
        + "\n".join(dict.fromkeys(includes))
        + "\n\n"
        + "\n".join(f[1] for f in helpers)
        + "\n"
    )

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
