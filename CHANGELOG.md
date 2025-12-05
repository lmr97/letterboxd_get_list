# Changelog

## 1.6.3 - 2025-12-04

### Fixed

- Fix bug where `IsADirectory` error is raised only after all films have been collected

## 1.6.2 - 2025-12-04

### Added

- Add more robust error handling, especially to handle `None`s

## 1.6.1 - 2025-09-02

### Fixed

- Fix misalignment of header column and data

## 1.6.0 - 2025-09-01

### Added

- Add multithreading for a massive performance increase (~10x speedup)

### Changed

- Change CLI to alphabetize attribute headers in CSV output file

## 1.5 - 2025-06-09

### Fixed

- Fixed the CSS selector in the stats-getting methods on `LetterboxdFilm`, following new website format on Letterboxd stats pages ([d3edc21](https://github.com/lmr97/letterboxd_get_list/commit/d3edc21a485e3e734ddc78a75cbe5bff9b14ff70))

### Added

- This changelog