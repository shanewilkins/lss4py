script <- grep("^--file=", commandArgs(), value = TRUE)
source(file.path(dirname(normalizePath(sub("^--file=", "", script[[1]]))), "common.R"))
dir.create(bootstrap_library, recursive = TRUE, showWarnings = FALSE)
use_library(bootstrap_library)
installed_version <- tryCatch(
  as.character(utils::packageVersion("renv", lib.loc = bootstrap_library)),
  error = function(e) ""
)
if (installed_version != "1.3.1") {
  # Exact source version, with archive fallback when CRAN advances.
  urls <- c("https://cloud.r-project.org/src/contrib/renv_1.3.1.tar.gz",
            "https://cloud.r-project.org/src/contrib/Archive/renv/renv_1.3.1.tar.gz")
  archive <- tempfile(fileext = ".tar.gz")
  downloaded <- FALSE
  for (url in urls) {
    downloaded <- tryCatch({
      utils::download.file(url, archive, mode = "wb", quiet = TRUE) == 0
    }, error = function(e) FALSE)
    if (downloaded) break
  }
  if (!downloaded) stop("Could not download renv 1.3.1.")
  utils::install.packages(archive, repos = NULL, type = "source", lib = bootstrap_library)
  unlink(archive)
}
stopifnot(as.character(utils::packageVersion("renv")) == "1.3.1")
renv::consent(provided = TRUE)
renv::restore(project = project, library = library,
              lockfile = file.path(project, "renv.lock"), prompt = FALSE)
cat("Locked R reference library restored. Run tools/r-reference/verify.R next.\n")
