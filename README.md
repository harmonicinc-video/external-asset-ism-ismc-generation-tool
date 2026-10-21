# ISM/ISMC manifests generation

harmonic_external_asset_ism_ismc_generation_tool is a command line tool to generate the ISM/ISMC manifest for the .mp4 files stored in Azure containers.
The tool parses .mp4 and .cmft files from an Azure container, generates .ism and .ismc manifests if they do not exist, and loads them into the Azure container. 

## Prerequisites
- Python 3.12+
- Python libs:
  - azure-core==1.29.4
  - azure-storage-blob==12.8.1
  - azure-identity==1.14.1
  - construct==2.8.8
  - pycountry==23.12.7
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
WebVTT-to-CMFT conversion is supported in local mode as well as Azure mode.

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
Parsing runs in a single process by default. The `-is_multithreading` flag enables
worker processes using the available CPU count. A media parsing failure aborts manifest
generation in either mode; it is not silently omitted from the output.

```
python3 main.py -local_copy
```
Run with local generation of ISM/ISMC (debug)

```
python3 main.py -no_overwrite_manifest
```
Disable replacement of canonical manifest names. This flag takes no value and sets
`overwrite_manifest=false`, overriding the configuration file. When omitted, the configuration
value is used; its default is `true` in local mode and `false` in Azure mode. When overwrite is
disabled, the tool preserves existing manifests and creates a matching `_new`, `_new2`, ...
ISM/ISMC pair. To enable overwriting explicitly, set `"overwrite_manifest": true` in the
configuration file; there is no positive CLI flag.

### Configuration file
The application also supports the following configuration options in `azure_config.json`:

### overwrite_manifest (boolean, mode-specific default)
Controls whether canonical manifest names are replaced. When omitted, it defaults to `true` in
local mode and `false` in Azure mode. The value-free `-no_overwrite_manifest` CLI flag overrides
this value to `false`; omitting the flag leaves the configuration value unchanged.

### align_start_times (boolean, default: true)
MP4 edit lists (`edts/elst`, versions 0 and 1) are applied before generating the ISMC.
Leading empty edits delay the presentation start; media-time edits trim the beginning
of the media, and finite edit durations limit its end. Video composition offsets
(`ctts`) are accounted for so that a composition-delay edit is not trimmed twice.
Movie edit durations use the `mvhd` timescale, while media times use the track's
`mdhd` timescale. ISMC timestamps use the manifest timescale (10,000,000 ticks/second).

- **true**: align all audio/video streams to the latest A/V presentation start and
  emit `StreamStartTimestamp` on each A/V `StreamIndex`. Earlier media is trimmed,
  not shifted: subsequent segment boundaries and stream end times are preserved.
  This is the downstream-packager compatibility mode. Subtitle timing is unchanged.
- **false**: preserve individual edit-derived presentation starts in the first
  `<c t="...">` and omit `StreamStartTimestamp`.

Set this in `azure_config.json` for either local or Azure processing:
```json
{
  "align_start_times": true
}
```
The value-free CLI flag `-no_align_start_times` overrides this setting to `false`.
When omitted, the configuration value is used, defaulting to `true`. To enable
alignment explicitly, set `"align_start_times": true` in the configuration file;
there is no positive CLI flag. Neither negative flag accepts `true` or `false` as a value.
For example:
```bash
python3 main.py -local_directory=/path/to/assets -no_align_start_times
```

For `room02.mp4`, the video empty edit is 1.92 seconds and the audio media-time
trim is 0.64 seconds. With alignment disabled, video starts at 1.92 seconds and
audio starts at zero with a 3.2-second first segment (`room02_offsetV.ismc`).
With alignment enabled, both start at 1.92 seconds and the first audio segment
is 1.28 seconds (`room02_offsetAV.ismc`). The presentation duration is unchanged.

Edit lists are the standard ISO BMFF mechanism for mapping media composition
time onto movie presentation time; see the
[ISO BMFF timing requirements](https://www.w3.org/TR/mse-byte-stream-format-isobmff/#iso-init-segments).
Their translation into a packager's ISMC input is an interoperability contract:
aligned starts and `StreamStartTimestamp` are not a universal MP4 requirement.
Supported edit sequences are leading empty edits followed by one normal-rate
media edit. Dwell/rate-changing edits and multiple media edits are rejected
explicitly rather than silently producing incorrect timing. A zero media-edit
duration extends through all remaining media. Alignment fails explicitly if
an A/V track ends at or before the common start. Missing, malformed, or duplicate edit
lists inside an edit box, nonpositive edit timescales, and edits that select no media
also abort generation. An absent edit box or a valid empty edit list has no timing effect.
Invalid `align_start_times` configuration values are reported as configuration errors;
use JSON booleans, not strings such as `"false"`.

The composition-delay mapping uses the initial `ctts` offset; it does not re-segment
individual sample presentation timestamps or rewrite the MP4. End-to-end DASH/HLS
playback still needs validation with the downstream packager.

### Manifest Generation Behavior
When manifests are generated:
- The manifest base name is chosen deterministically: an existing `.ism` name is preferred;
  otherwise the first supported media filename in case-insensitive sort order is used.
- Text, CMFT, and MPI index files are not used as the base name source.
- If `overwrite_manifest=true`: canonical `.ism`/`.ismc` names are replaced.
- If `overwrite_manifest=false`: existing manifests are preserved and a matching `_new`, `_new2`,
  ... pair is generated.

### convert_webvtt (boolean, default: false)
Controls how WebVTT files are handled:
- **false**: VTT files are added to manifests as raw WebVTT (FourCC="WVTT")
- **true**: VTT files are converted to IMSC1, packaged as CMFT, and added to manifests as CMFT (FourCC="IMSC")

## Utilities for Azure
```bash
python3 upload_azure_asset.py -asset_zip_name=<zip_file>     # unzip and upload an asset in Azure Blob (before calling the main process)
python3 list_azure_containers.py                           # list all containers in the storage account
python3 remove_azure_asset.py                              # delete the configured container and all its blobs
python3 remove_all_azure_containers.py                      # list containers and show the deletion command; delete nothing
python3 remove_all_azure_containers.py -confirm_account_name=<storage_account_name>
```

These utilities read `azure_config.json`; command-line settings override the file.
Listing and account-wide cleanup require `connection_string`. Single-asset removal
uses `container_name` to select the container.

**Warning:** `remove_all_azure_containers.py` deletes every listed container and all
its blobs, not just the configured `container_name`. Without confirmation, the script
only lists containers and hints at the command for deletion; there is no `-dry_run`
option. Preview is optional: delete in one command by supplying the exact connected
account name via `-confirm_account_name`. A wrong or empty confirmation is rejected;
confirmation cannot be supplied through the configuration file. This operation
cannot be undone by this tool; recoverability depends on Azure retention settings.
The script reports each deletion, continues after individual Azure deletion errors,
and exits nonzero if any deletion, listing, or setup operation fails. Containers
created after the initial listing are not included. Account credentials need both
container-listing and container-deletion permissions.

## Testing

Run tests with:
```bash
pytest
pytest tests/integration_tests/ -v # run test subset for manifest generation
pytest tests/conversion_tests/ -v # run test subset for manifest generation
```

Timing and CLI regressions can be run without the room02 MP4:
```bash
python3 -m pytest tests/test_local_media_data_parser.py tests/test_media_data_parser.py tests/test_settings_and_manifest_names.py tests/test_main.py -q
```
These cover binary edit-list versions, composition offsets, trimming, both room02
timelines, repeat counts, MPI timing replacement, configuration precedence, and error paths.

Generate JSON test assets with:
```bash
python3 generate_test_data.py -output_name=<output_file_without_extension>
```

## Key Directories

- `azure_client/` - Azure API management
- `blob_data_handler/` - Azure API management
- `file_processor/` - routing of file processing
- `media_data_parser/` - Processing of MP4 files
- `mss_client_manifest/` - Generation of ISMC manifest
- `mss_server_manifest/` - Generation of ISM manifest
- `text_data_parser/` - Processing of text files (WebVTT and TTML)

## IDR-Aligned Segment Detection

For non-fragmented MP4 files that carry no segmentation info, the tool must determine a segment duration for the manifest. It does so by detecting IDR (Instantaneous Decoder Refresh) pictures — the only frames where a decoder can safely start playback.

The algorithm reads the STSS (Sync Sample) box to identify sync samples, then fetches the first bytes of each sample's NAL units to verify whether they are true IDR frames (H.264 NAL type 5) or IRAP frames (H.265 NAL types 16–21), as opposed to non-IDR I-pictures which may also appear in STSS. Only the first 15 sync samples are inspected for efficiency.

If the IDR interval is constant, it is used as the segment period (with a 2-second minimum, doubling the period if needed). If not constant, the tool falls back to fixed 2-second segments. This ensures manifest segments align with actual random access points whenever possible, enabling seamless playback start and stream switching.

Supported video codecs: AVC (`avc1`) and HEVC (`hvc1`). For files without STSS data or for audio-only tracks, the original STSS list is used as-is without NAL filtering.

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
- VTT files are converted to CMFT during preprocessing in Azure and local modes
- Source VTT files are excluded from manifest generation after conversion
- Only generated CMFT files appear in manifests with FourCC "IMSC"

File extensions are processed case-insensitively in both modes. If a raw VTT or TTML file cannot
be parsed, it is skipped while processing continues for the remaining files.

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
- List of raw (non-converted) VTT/TTML subtitles that were skipped because they could
  not be parsed, with the reason for each
- Manifest generation status (created or skipped)
- Appears at the end of processing, after both VTT conversion and manifest generation

### Manifest Generation Failures

If manifest generation cannot proceed (for example, no `.ism` file and no supported media
file can be found to derive the manifest name from), the tool prints a one-line error
message and exits with a non-zero status instead of a raw stack trace.
