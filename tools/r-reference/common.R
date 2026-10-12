# Explicit opt-in tooling; never activate renv in the Python project root.
script <- grep("^--file=", commandArgs(), value = TRUE)
project <- dirname(normalizePath(sub("^--file=", "", script[[1]])))
if (getRversion() != "4.6.1") {
  stop("Reference tooling requires R 4.6.1; install that runtime separately.")
}
library <- file.path(project, ".library")
bootstrap_library <- file.path(project, ".bootstrap")
Sys.setenv(RENV_PATHS_ROOT = file.path(project, ".renv"),
           RENV_CONFIG_CACHE_ENABLED = "FALSE")
options(repos = c(CRAN = "https://cloud.r-project.org"), timeout = 300)

use_library <- function(path) {
  # Exclude user/site libraries so unrelated installations cannot fill gaps.
  .libPaths(c(path, .Library), include.site = FALSE)
}
