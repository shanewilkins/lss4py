script <- grep("^--file=", commandArgs(), value = TRUE)
source(file.path(dirname(normalizePath(sub("^--file=", "", script[[1]]))), "common.R"))
if (!dir.exists(library)) stop("Run tools/r-reference/bootstrap.R first.")
use_library(library)
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Restore the locked library first.")
lock <- jsonlite::read_json(file.path(project, "renv.lock"))
for (package in names(lock$Packages)) {
  installed <- utils::packageDescription(package, lib.loc = c(library, .Library))
  if (is.na(installed[[1]]) || installed$Version != lock$Packages[[package]]$Version) {
    stop(paste("Locked package missing or wrong version:", package))
  }
}

fixtures <- normalizePath(file.path(project, "../../tests/fixtures/reference/r-sixsigma-baseline"))
work <- tempfile("lss4py-r-reference-")
dir.create(work)
stopifnot(all(file.copy(file.path(fixtures, c("generate.R", "inputs.json")), work)))
status <- system2(file.path(R.home("bin"), "Rscript"),
                  c("--vanilla", shQuote(file.path(work, "generate.R"))),
                  env = c(paste0("R_LIBS_USER=", shQuote(library)),
                          "R_LIBS_SITE=NULL", "R_LIBS=NULL"))
if (status != 0) stop("R reference generation failed.")

compare <- function(actual, expected, tolerance, path) {
  if (is.numeric(expected) && is.numeric(actual)) {
    if (length(actual) != length(expected) ||
        any(abs(actual - expected) > tolerance$absolute + tolerance$relative * abs(expected))) {
      stop(paste("Numerical mismatch:", path))
    }
  } else if (is.list(expected) && is.list(actual)) {
    if (length(actual) != length(expected) || !identical(names(actual), names(expected))) {
      stop(paste("Structure mismatch:", path))
    }
    for (i in seq_along(expected)) {
      compare(actual[[i]], expected[[i]], tolerance, paste0(path, "/", i))
    }
  } else if (!identical(actual, expected)) {
    stop(paste("Exact-value mismatch:", path))
  }
}
for (artifact in c("expected.json", "invalid.json")) {
  expected <- jsonlite::read_json(file.path(fixtures, artifact))
  actual <- jsonlite::read_json(file.path(work, artifact))
  if (length(actual) != length(expected)) stop("Reference case count mismatch.")
  for (i in seq_along(expected)) {
    # Tolerate only numerical results; parameters and all metadata remain exact.
    compare(actual[[i]]$expected, expected[[i]]$expected, expected[[i]]$tolerance,
            paste(artifact, expected[[i]]$id))
    actual[[i]]$expected <- expected[[i]]$expected
    if (!identical(actual[[i]], expected[[i]])) stop("Reference case metadata mismatch.")
  }
}
unlink(work, recursive = TRUE)
cat("All 20 SixSigma reference cases reproduced within declared tolerances.\n")
