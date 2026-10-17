
"""API routes for single-code C++ splitting."""

from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.source_splitter import split_source
from backend.compile_benchmark import compare_compilation

router = APIRouter(prefix="/api/split", tags=["Source Splitting"])

MAX_SOURCE_SIZE = 100 * 1024


@router.post("/analyze")
async def analyze_single_code(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".cpp"):
        raise HTTPException(400, "Please upload a .cpp file")

    content = await file.read(MAX_SOURCE_SIZE + 1)

    if not content or len(content) > MAX_SOURCE_SIZE:
        raise HTTPException(400, "Source must be 1-100 KB")

    try:
        source_text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "Source must be UTF-8")

    try:
        with TemporaryDirectory(prefix="harp_split_") as temp:
            work_dir = Path(temp)
            source_path = work_dir / "input.cpp"
            generated_dir = work_dir / "generated"
            source_path.write_bytes(content)
            print("UPLOAD DEBUG")
            print("Filename:", file.filename)
            print("Uploaded bytes:", len(content))
            print("File bytes:", source_path.stat().st_size)
            print("First 60 bytes:", repr(source_path.read_bytes()[:60]), flush=True)

            split_result = split_source(source_path, generated_dir)
            from tree_sitter import Language, Parser
            import tree_sitter_cpp

            debug_bytes = source_path.read_bytes()
            debug_parser = Parser(Language(tree_sitter_cpp.language()))
            debug_tree = debug_parser.parse(debug_bytes)

            print("=== SPLITTER DIAGNOSTICS ===", flush=True)
            print("Uploaded filename:", file.filename, flush=True)
            print("Uploaded size:", len(content), flush=True)
            print("Original and saved bytes match:", content == debug_bytes, flush=True)
            print("Parser has error:", debug_tree.root_node.has_error, flush=True)
            print("Parser tree:", str(debug_tree.root_node)[:1500], flush=True)
            print("============================", flush=True)
            benchmark = compare_compilation(
                source_path, generated_dir
            )

            generated_files = [
                {
                    "filename": Path(name).name,
                    "code": Path(name).read_text(encoding="utf-8"),
                }
                for name in split_result.generated_files
            ]

            return {
                "success": True,
                "message": split_result.message,
                "generatedFiles": generated_files,
                "benchmark": benchmark,
            }

    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(
            422,
            f"Compilation or splitting failed: {exc}"
        ) from exc
