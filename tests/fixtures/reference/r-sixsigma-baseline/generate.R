# Original LSS4PY reference generator, MIT license (see repository LICENSE.md).
# Requires the genuine installed SixSigma 0.11.1 namespace; no copied R kernels.
args <- commandArgs(trailingOnly = TRUE)
verify <- "--verify" %in% args
script_arg <- grep("^--file=", commandArgs(), value = TRUE)
root <- dirname(normalizePath(sub("^--file=", "", script_arg[[1]])))
stopifnot(requireNamespace("SixSigma", quietly = TRUE))
stopifnot(requireNamespace("jsonlite", quietly = TRUE))
stopifnot(as.character(utils::packageVersion("SixSigma")) == "0.11.1")
inputs <- jsonlite::read_json(file.path(root, "inputs.json"), simplifyVector = TRUE)
x <- inputs$columns$x

observe <- function(api, arguments) {
  warnings <- character()
  result <- tryCatch(
    withCallingHandlers(
      do.call(getExportedValue("SixSigma", api), arguments),
      warning = function(w) {
        warnings <<- c(warnings, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) e
  )
  if (inherits(result, "error")) {
    return(list(status = "error", error_class = class(result),
                message = conditionMessage(result), warnings = as.list(warnings)))
  }
  list(status = "returned", value = result, result_class = class(result),
       warnings = as.list(warnings))
}

reference <- function(id, api, arguments) {
  list(id = id, method = api, input_kind = "r_arguments", parameters = arguments,
       expected = observe(api, arguments),
       tolerance = list(absolute = 1e-12, relative = 1e-12),
       tolerance_reason = "Retain 17-digit R output; future Python estimates use float64 tolerances.",
       basis = "Executed the exported function in the installed SixSigma 0.11.1 package.")
}

expected <- list(
  reference("cp-two-sided", "ss.ca.cp", list(x = x, LSL = 6, USL = 14)),
  reference("cp-upper-only", "ss.ca.cp", list(x = x, USL = 14)),
  reference("cp-confidence", "ss.ca.cp", list(x = x, LSL = 6, USL = 14, ci = TRUE)),
  reference("cpk-offset", "ss.ca.cpk", list(x = x, LSL = 7, USL = 14)),
  reference("cpk-confidence", "ss.ca.cpk", list(x = x, LSL = 7, USL = 14, ci = TRUE)),
  reference("z-two-sided", "ss.ca.z", list(x = x, LSL = 7, USL = 14)),
  reference("z-long-term", "ss.ca.z", list(x = x, LSL = 7, USL = 14, LT = TRUE)),
  reference("z-lower-only", "ss.ca.z", list(x = x, LSL = 7)),
  reference("z-upper-only", "ss.ca.z", list(x = x, USL = 14)),
  reference("z-negative", "ss.ca.z", list(x = x, LSL = 11, USL = 14)),
  reference("z-lower-shifted", "ss.ca.z", list(x = x, LSL = 7, LT = TRUE)),
  reference("z-upper-shifted", "ss.ca.z", list(x = x, USL = 14, LT = TRUE)),
  reference("z-negative-shifted", "ss.ca.z", list(x = x, LSL = 11, USL = 14, LT = TRUE)),
  reference("yield-with-rework", "ss.ca.yield", list(
    defects = inputs$columns$defects, rework = inputs$columns$rework, opportunities = 100
  )),
  reference("yield-zero-defects", "ss.ca.yield", list(defects = c(0, 0),
                                                      rework = c(0, 0), opportunities = 100))
)
invalid <- list(
  reference("cp-no-limits", "ss.ca.cp", list(x = x)),
  reference("cpk-nonnumeric", "ss.ca.cpk", list(x = c("a", "b"), LSL = 6, USL = 14)),
  reference("z-no-limits", "ss.ca.z", list(x = x)),
  reference("yield-zero-opportunities", "ss.ca.yield", list(
    defects = c(1, 2), rework = c(0, 1), opportunities = 0
  )),
  reference("yield-length-mismatch", "ss.ca.yield", list(
    defects = c(1, 2, 3), rework = c(0, 1), opportunities = 100
  ))
)

save_or_verify <- function(name, value) {
  path <- file.path(root, name)
  # NA/NaN/Inf are tagged strings, never nonstandard JSON numeric literals.
  content <- as.character(jsonlite::toJSON(value, auto_unbox = TRUE,
                                          pretty = TRUE, digits = 17, na = "string"))
  if (verify) {
    stopifnot(identical(paste(readLines(path, warn = FALSE), collapse = "\n"), content))
  } else {
    writeLines(content, path, useBytes = TRUE)
  }
}
save_or_verify("expected.json", expected)
save_or_verify("invalid.json", invalid)
if (!verify) {
  provenance <- list(
    package = "SixSigma", package_version = as.character(utils::packageVersion("SixSigma")),
    r_version = R.version.string, platform = R.version$platform,
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    jsonlite_version = as.character(utils::packageVersion("jsonlite")),
    command = "Rscript --vanilla tests/fixtures/reference/r-sixsigma-baseline/generate.R",
    nonfinite_encoding = "jsonlite na=string: NA/NaN/Inf/-Inf are string tokens",
    session_info = capture.output(utils::sessionInfo())
  )
  save_or_verify("provenance.json", provenance)
}
cat(if (verify) "R reference outputs reproduced exactly\n" else "R reference outputs generated\n")
