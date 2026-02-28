# OpenGeoTIFF - library for processing GeoTIFF files

## Overview
The `OpenGeoTIFF` library provides a simple command line interface for automatically retrieving GeoTIFF images from a remote data repository and then processing the image to produce vectorized GKPG files. 

A `yml` configuration file is used to provide key parameters to the library.

## Key features

- Run simple binary processing through `min` and `max` settings.
- Clip to a user-supplied outline.

## Installation

```
pip install git+https://github.com/opensiteenergy/opengeotiff.git
```

To use the library, enter:

```
opengeotiff /path/to/conf.yml
```

## Configuration file

The `.yml` configuration file should have the following format:

```
# ----------------------------------------------------
# sample.yml
# Sample yml configuration file
# ----------------------------------------------------

# Link to this GitHub code repository 
# This can be used to host yml files on an open data server and automatically install required library just-in-time
codebase:
  https://github.com/opensiteenergy/opengeotiff.git

# Link to Solargis 1km resolution solar irradiation GeoTIFF
# https://solargis.com/resources/free-maps-and-gis-data?locality=united-kingdom
# Solar resource map © 2021 Solargis [https://solargis.com]
source:
  https://cms.solargis.com/file?url=download/United%20Kingdom/United-Kingdom_GISdata_LTAym_YearlyMonthlyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip&bucket=globalsolaratlas.info#GTI.tif

# Directory where downloaded tiles and temporary data are stored
cache_dir:
  ./cache/opengeotiff

# External URL or path to a geometry file used to crop the output to a specific shape
clipping:
  https://github.com/opensiteenergy/opensiteenergy/raw/refs/heads/main/clipping-master-EPSG-25830.gpkg

# The exact name and extension of the final file generated
output:
  solar-insufficient-solar-irradiation--uk.gpkg

# Filters the final result values
# We only want to select points with insufficient irradiation which is typically 1000 kWh/m2/year
mask:
  # Minimum kWh/m2/year
  min: 
    0
  
  # Maximum kWh/m2/year
  max: 
    1000
```

## Possible uses

- Generating areas with insufficient solar irradiation for solar farm siting.

