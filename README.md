# ISM/ISMC manifests generation

harmonic_external_asset_ism_ismc_generation_tool is a command line tool to generate the ISM/ISMC manifest for the .mp4 files stored in Azure containers.
The tool parses .mp4 and .cmft files from an Azure container, generates .ism and .ismc manifests if they do not exist, and loads them into the Azure container. 

## Prerequisites
- Python 3.10+
- Python libs:
  - azure-core==1.29.4
  - azure-storage-blob==12.8.1
  - azure-identity==1.14.1
  - construct==2.8.8
  - pycountry==22.3.5
  - webvtt-py==0.5.1
  - ttconv==1.2.0

## Supported codecs
### Video codecs
- AVC
- HEVC
### Audio codecs
- AAC-LC
- AAC-HE (when it's compatible with AAC-LC and we interpret it as AAC-LC)
- E-AC3
### Subtitles
- WebVTT (conversion to IMSC1)

## Supported extensions:
### media formats:
- .mp4
- .mpi
- .ismv
- .isma
- .cmft

### text formats
- .ttml (raw mode only)
- .vtt (raw mode and conversion to CMFT)

## How to run
### With Azure Storage
```
python3 main.py -connection_string=<Azure storage account's connection string> -container_name=<Azure container name>
```
or
```
python3 main.py
```
in case if the configuration file azure_config.json has been filled (the configuration file shall be situated in the same folder as the main.py file).

### With Local Directory
```
python3 main.py -local_directory=/path/to/directory/with/mp4/files
```
This mode processes MP4 files from a local directory and generates ISM/ISMC manifests in the same directory. This option is completely independent of Azure and does not require any Azure configuration.

### azure_config.json
azure_config.json - configuration file may contain the following fields: connection_string, account_name, account_key, container_name:
```
{
  "connection_string": "DefaultEndpointsProtocol=https;AccountName=flametestextassetstorage;AccountKey=<key>;EndpointSuffix=core.windows.net",
  "account_name": "flametestextassetstorage",
  "account_key": "<key>",
  "container_name": "test2"
}
```
**Note:** The `local_directory` option is only available as a command-line argument (`-local_directory`) and cannot be configured in the azure_config.json file.
It's possible to set the `connection_string`  field or `account_name` and `account_key` .
If only the `account_name` and `account_key` fields are specified, the connection string is formed from them.
If all fields are set, only the `connection_string` field value is used. In this case the `account_name` and `account_key` fields are ignored.

Azure connection string can be found in Azure Portal → Storage container → Access keys → Connection string

## Configuration Options

### command-line
```
python3 main.py -is_multithreading
```
Currently ISM/ISMC generation tool supports two modes: one-threaded and multi-threaded. Multi-threaded mode uses the maximum amount of threads your system can handle.

```
python3 main.py --local_copy
```
Run with local generation of ISM/ISMC (debug)

### Configuration file
The application also supports the following configuration options in `azure_config.json`:

### Manifest Generation Behavior
When manifests are generated:
- If **no manifest exists**: A new manifest file (.ism/.ismc) is created with the standard name
- If **a manifest already exists**: A new manifest is generated with the suffix `_new` appended to the filename (e.g., `asset_new.ism`, `asset_new.ismc`)
- This ensures existing manifests are preserved while allowing new manifests to be generated

### convert_webvtt (boolean, default: false)
Controls how WebVTT files are handled:
- **false**: VTT files are added to manifests as raw WebVTT (FourCC="WVTT")
- **true**: VTT files are converted to IMSC1, packaged as CMFT, and added to manifests as CMFT (FourCC="IMSC")

## Utilities for Azure
```bash
python3 upload_asset.py     # unzip and upload an asset in Azure Blob (before calling the main process)
python3 remove_asset.py     # remove an asset from Azure Blob
```

## Testing

Run tests with:
```bash
pytest
pytest tests/integration_tests/ -v # run test subset for manifest generation
pytest tests/conversion_tests/ -v # run test subset for manifest generation
```

## Key Directories

- `azure_client/` - Azure API management
- `blob_data_handler/` - Azure API management
- `file_processor/` - routing of file processing
- `media_data_parser/` - Processing of MP4 files
- `mss_client_manifest/` - Generation of ISMC manifest
- `mss_server_manifest/` - Generation of ISM manifest
- `text_data_parser/` - Processing of text files (WebVTT and TTML)

## VTT to CMFT feature

A new feature has been added: converting WebVTT files found in the Azure container to CMFT files before manifest generation.

### Process Overview

It runs automatically when `convert_webvtt=true`:
WebVTT files in the container are detected based on their extension (.vtt), then converted to MP4/CMFT files and updated to the Blob container.

This process runs before the `generate_manifests()` call, so that created CMFT files will be processed during the manifest generation.

## Implementation Details

### VTT to CMFT Conversion Pipeline

When `convert_webvtt=true`, the application performs a 5-step operation:

1. **Detection**: Identifies WebVTT files (.vtt) in the Azure Blob container
2. **IMSC1 Conversion**: Converts WebVTT to IMSC1 format using the `ttconv` library
3. **Segmentation**: Segments the IMSC1 file using a fixed segment duration (4 seconds)
4. **CMFT Packaging**: Packages segmented IMSC1 into an MP4/CMFT file using the `pymp4`library:
   - Structure: ftyp + moov (with mdhd language encoding) + moof/mdat pairs (one per segment)
5. **Upload**: Uploads the generated CMFT file to the Azure Blob container

### Language Code Extraction

Language codes are extracted from filenames using pattern matching:
- Uses regex `re.split(r'[_\-\.]', filename)` to split on underscores, hyphens, or dots
- Searches all filename segments for 3-letter ISO 639-2/T codes
- Position-independent: Works with `espn1_ARA.vtt`, `ARA_espn1.vtt`, or `espn1.ara.vtt`
- For CMFT files already present: use track metadata language (from mdhd atom) if present, otherwise filename extraction
- if no 3-letter code is found in the VTT file name, the language is set to 'und'

### Language Code Embedding

Language codes are embedded at three levels to ensure proper signalization:
- The `xml:lang` attribute is set on the root `<tt>` element
- Language is encoded in the `mdhd` atom of the CMFT track using 16-bit MP4 format
- The `systemLanguage` attribute is added to text streams in ISM manifests

### VTT File Handling Modes

**Mode 1: convert_webvtt = false** (default)
- VTT files are processed as-is and added to manifests
- FourCC in manifest: "WVTT"

**Mode 2: convert_webvtt = true**
- VTT files are converted to CMFT during preprocessing
- VTT files are excluded from manifest generation (handled by `blob_data_handler.py`)
- Only generated CMFT files appear in manifests with FourCC "IMSC"

## Error Handling

### VTT to IMSC1 Conversion Errors

**Input Validation**:
- **Empty VTT Content**: Detects and reports empty or whitespace-only VTT content before processing
- **Error Message**: "VTT content is empty or contains only whitespace"

**HTML Sanitization** (when `sanitize_html=True`, default):
- **Automatic Fix**: Removes malformed HTML tags while preserving valid VTT tags (b, i, u, ruby, rt, v, c, lang)
- **Logging**: Reports each fixed issue with cue number and specific tags removed

**Conversion Errors**:
- **AttributeError**: Malformed VTT structure or missing required elements
- **TypeError**: Invalid cue text or HTML parsing issues  
- **ValueError**: Invalid timing formats or other validation errors
- **UnicodeDecodeError**: Character encoding problems

### IMSC1 Segmentation Errors

**XML Parsing Errors**:
- **ET.ParseError**: Invalid XML syntax in IMSC1 content

**Structure Validation**:
- **Missing body element**: IMSC1 missing required `<body>` element
- **Missing div element**: IMSC1 missing required `<div>` element inside body

### CMFT Packaging Errors

**Data Validation**:
- **ValueError**: Invalid segment data or structure
- **struct.error**: Binary data packing issues

### Conversion Summary

After processing completes, a comprehensive summary is displayed showing both VTT conversion and manifest generation results.

The summary provides:
- VTT conversion statistics (successful/total)
- List of files with sanitization warnings (automatically fixed HTML issues)
- List of failed files with specific error reasons
- Manifest generation status (created or skipped)
- Appears at the end of processing, after both VTT conversion and manifest generation
