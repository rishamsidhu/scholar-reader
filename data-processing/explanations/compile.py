import configparser
import csv
import logging
import os
import os.path
import re
import subprocess
from typing import Iterator, List

from explanations.types import CompilationResult

COMPILE_CONFIG = "config.ini"
PDF_MESSAGE_PREFIX = b"Generated PDF: "
PDF_MESSAGE_SUFFIX = b"<end of PDF name>"
POSTSCRIPT_MESSAGE_PREFIX = b"Generated PostScript: "
POSTSCRIPT_MESSAGE_SUFFIX = b"<end of PostScript name>"


def _get_generated_pdfs(stdout: bytes) -> List[str]:
    pdfs = re.findall(
        PDF_MESSAGE_PREFIX + b"(.*)" + PDF_MESSAGE_SUFFIX, stdout, flags=re.MULTILINE
    )
    return [pdf_name_bytes.decode("utf-8") for pdf_name_bytes in pdfs]


def _get_generated_postscript_filenames(stdout: bytes) -> List[str]:
    postscript_filenames = re.findall(
        POSTSCRIPT_MESSAGE_PREFIX + b"(.*)" + POSTSCRIPT_MESSAGE_SUFFIX,
        stdout,
        flags=re.MULTILINE,
    )
    return [
        postscript_name_bytes.decode("utf-8")
        for postscript_name_bytes in postscript_filenames
    ]


def _set_sources_dir_permissions(sources_dir: str) -> None:
    """
    AutoTeX requires permissions to be 0777 or 0775 before attempting compilation.
    """
    COMPILATION_PERMISSIONS = 0o775
    os.chmod(sources_dir, COMPILATION_PERMISSIONS)
    for (dirpath, dirnames, filenames) in os.walk(sources_dir):
        for filename in filenames:
            os.chmod(os.path.join(dirpath, filename), COMPILATION_PERMISSIONS)
        for dirname in dirnames:
            os.chmod(os.path.join(dirpath, dirname), COMPILATION_PERMISSIONS)


def compile_tex(sources_dir: str) -> CompilationResult:
    """
    Compile TeX sources into PDFs. Requires running an external script to attempt to compile
    the TeX. See README.md for dependencies.
    """
    logging.debug("Compiling sources in %s", sources_dir)
    _set_sources_dir_permissions(sources_dir)

    config = configparser.ConfigParser()
    config.read(COMPILE_CONFIG)
    texlive_path = config["tex"]["texlive_path"]
    texlive_bin_path = config["tex"]["texlive_bin_path"]

    postprocessors = {}
    if "tex-postprocessors" in config:
        for name, command in config["tex-postprocessors"].items():
            postprocessors[name] = command

    if "perl" in config and "binary" in config["perl"]:
        perl_binary = config["perl"]["binary"]
    else:
        perl_binary = "perl"

    result = subprocess.run(
        [
            perl_binary,
            os.path.join("perl", "compile_tex.pl"),
            sources_dir,
            texlive_path,
            texlive_bin_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    success = False
    postprocesing_error = False
    if result.returncode == 0:

        success = True
        pdfs = _get_generated_pdfs(result.stdout)
        output_files = {
            "postscript": _get_generated_postscript_filenames(result.stdout)
        }

        for output_type, filenames in output_files.items():
            if output_type not in postprocessors or len(filenames) == 0:
                continue

            command = postprocessors[output_type]
            try:
                generated_pdfs = process_files(command, sources_dir, filenames)
                if len(generated_pdfs) == 0:
                    logging.warning(
                        "No PDF files generated with postprocessor for output type %s",
                        output_type,
                    )
                pdfs.extend(generated_pdfs)
            except PostProcessorException as e:
                logging.error("Post-processing error: %s", e)
                postprocesing_error = True
                success = False

    return CompilationResult(
        success, pdfs, result.stdout, result.stderr, postprocesing_error
    )


class PostProcessorException(Exception):
    """
    Exception raised on the failure of a post-processor.
    """


PdfFileName = str


def process_files(
    command: str, sources_dir: str, filenames: List[str]
) -> List[PdfFileName]:
    """
    Run a post-processing command on a set of files. 'command' should take one parameter (the
    name of the file to process) and produce a new file with the same basename and the
    '.pdf' extension.
    """
    pdfs: List[PdfFileName] = []
    for filename in filenames:
        basename, _ = os.path.splitext(filename)

        logging.debug("Processing file %s with command %s", filename, command)
        result = subprocess.run(
            [command, filename],
            cwd=sources_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if result.returncode != 0:
            raise PostProcessorException(
                f"Error processing file {filename} from directory {sources_dir}"
                + f"with command {command}:"
                + result.stderr.decode("utf-8")
            )

        logging.debug("Successfully ran command %s on file %s", command, filename)
        pdf = basename + ".pdf"
        pdfs.append(pdf)

    return pdfs


def get_compiled_pdfs(compiled_tex_dir: str) -> List[str]:
    """
    Get a list of paths to compiled PDFs in a directory of compiled TeX.
    Returned paths are relative to the working directory of compilation. In most cases, this will
    either be relative to <data-directory>/<arxiv-id>, or to <data-directory>/<arxiv-id>/<iteration>/
    """
    compilation_results_dir = os.path.join(compiled_tex_dir, "compilation_results")
    result_path = os.path.join(compilation_results_dir, "result")
    with open(result_path) as result_file:
        result = result_file.read().strip()
        if result == "True":
            pdf_paths = []
            pdf_names_path = os.path.join(compilation_results_dir, "pdf_names.csv")
            with open(pdf_names_path) as pdf_names_file:
                reader = csv.reader(pdf_names_file)
                for row in reader:
                    pdf_paths.append(row[1])
            return pdf_paths

    return []


def get_errors(tex_engine_output: bytes, context: int = 5) -> Iterator[bytes]:
    """
    Extract a list of TeX errors from the TeX compiler's output. 'context' is the number of
    lines to extract after each error symbol ('!'). The list of errors produced by this method may
    be inaccurate and incomplete.
    """
    lines = tex_engine_output.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(b"!"):
            yield b"\n".join(lines[i : i + context])


def is_driver_unimplemented(tex_engine_output: bytes) -> bool:
    # This string should be exactly the same as the one that we program the color command to emit
    # when no driver is found, in 'color_commands.tex'.
    return br"Coloring not implemented for driver" in tex_engine_output
