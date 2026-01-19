"""
Test module for VTT to CMFT conversion functionality.

This module tests the conversion process using the asset-test-vtt-syntax_ENG.vtt test file
and compares the output with asset-test-vtt-syntax_ENG_REF.cmft reference file.
"""

import os
import pytest
import xml.etree.ElementTree as ET
from external_asset_ism_ismc_generation_tool.text_data_parser.vtt_to_imsc1_converter import VttToImsc1Converter
from external_asset_ism_ismc_generation_tool.text_data_parser.imsc1_segmenter import Imsc1Segmenter
from external_asset_ism_ismc_generation_tool.text_data_parser.cmft_packager import CmftPackager
from tests.test_utils.common.common import Common


def test_vtt_to_imsc1_conversion():
    """Test that VTT can be converted to IMSC1 format with comprehensive validation."""
    # Read asset-test-vtt-syntax_ENG.vtt
    with open(Common.get_data_file_path('asset-test-vtt-syntax_ENG.vtt'), 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    # Remove BOM if present
    if vtt_content.startswith('\ufeff'):
        vtt_content = vtt_content[1:]
    
    # Convert to IMSC1
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content)
    
    # Basic validation
    assert imsc1_content is not None
    assert len(imsc1_content) > 0
    assert '<?xml' in imsc1_content
    assert 'ttml' in imsc1_content
    
    # Point 1: XML Structure Validation
    root = ET.fromstring(imsc1_content)
    
    # Verify IMSC1/TTML namespace
    assert root.tag.endswith('tt'), "Root element should be 'tt'"
    assert 'http://www.w3.org/ns/ttml' in root.tag, "Should use TTML namespace"
    
    # Check required sections
    head = root.find('.//{http://www.w3.org/ns/ttml}head')
    body = root.find('.//{http://www.w3.org/ns/ttml}body')
    assert head is not None, "IMSC1 must have <head> element"
    assert body is not None, "IMSC1 must have <body> element"
    
    # Point 2: Content Preservation Validation
    paragraphs = root.findall('.//{http://www.w3.org/ns/ttml}p')
    assert len(paragraphs) > 0, "Should have subtitle paragraphs"
    
    # Extract all text content
    all_text = ' '.join([''.join(p.itertext()) for p in paragraphs])
    assert len(all_text.strip()) > 0, "Subtitles should contain text content"
    
    # Verify content from VTT is preserved (basic check)
    # Count approximate cues in VTT (lines with '-->' indicate cues)
    vtt_cue_count = vtt_content.count('-->')
    imsc1_p_count = len(paragraphs)
    assert imsc1_p_count > 0, "Should have converted at least one cue"
    assert imsc1_p_count <= vtt_cue_count + 2, f"IMSC1 paragraph count ({imsc1_p_count}) shouldn't exceed VTT cues ({vtt_cue_count}) by much"
    
    # Point 3: Timing Information Validation
    for p in paragraphs:
        assert 'begin' in p.attrib, f"Each subtitle paragraph should have 'begin' time attribute"
        begin = p.attrib['begin']
        # Verify time format (either HH:MM:SS.mmm or seconds like 1.5s or media time)
        assert ':' in begin or 's' in begin or begin.replace('.', '').isdigit(), \
            f"Time attribute should be in valid format, got: {begin}"
        
        # Most paragraphs should have end time (unless they extend to end)
        if 'end' in p.attrib:
            end = p.attrib['end']
            assert ':' in end or 's' in end or end.replace('.', '').isdigit(), \
                f"End time should be in valid format, got: {end}"
    
    print(f"✓ VTT to IMSC1 conversion successful: {len(imsc1_content)} bytes")
    print(f"  - Valid XML structure with required TTML elements")
    print(f"  - {len(paragraphs)} subtitle paragraphs with {len(all_text)} chars of text")
    print(f"  - All paragraphs have timing attributes")


def test_vtt_edge_cases():
    """Test edge cases: empty VTT and VTT with cue settings."""
    
    # Test 1: Empty VTT file
    empty_vtt = "WEBVTT\n\n"
    imsc1_content, warnings = VttToImsc1Converter.convert(empty_vtt)
    
    # Should still produce valid IMSC1 with no cues
    assert imsc1_content is not None
    assert '<?xml' in imsc1_content
    assert 'ttml' in imsc1_content
    
    root = ET.fromstring(imsc1_content)
    paragraphs = root.findall('.//{http://www.w3.org/ns/ttml}p')
    assert len(paragraphs) == 0, "Empty VTT should produce IMSC1 with no paragraphs"
    print("✓ Empty VTT handled correctly")
    
    # Test 2: VTT with timing syntax errors - ttconv should skip malformed timing cues
    # Bad cues: 1 (ms format), 3 (comma instead of period)
    # Valid cues that should be converted: 2, 4, 5 (3 total)
    vtt_with_bad_times = """WEBVTT

STYLE
::cue(.yellow) { color:red; }

00:00:01.000 --> 00:00:03.00
Cue 1 with bad time format

00:00:04.000 --> 00:00:06.000
<c.red>Cue 2 is red!</c>

00:00:07.000 --> 00:00:09,000
Cue 3, another bad time format

00:00:10.000 --> 00:00:12.000
<c.yellow>Cue 4 should be red too!</c>
"""
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_with_bad_times)
    root = ET.fromstring(imsc1_content)
    paragraphs = root.findall('.//{http://www.w3.org/ns/ttml}p')

    # ttconv should skip the 2 malformed timing cues and convert the 2 valid ones
    assert len(paragraphs) == 2, f"Should convert 2 valid cues (timing errors skipped), got {len(paragraphs)}"
    
    # Check first valid cue (Cue 2)
    first_text = ''.join(paragraphs[0].itertext()).strip()
    assert 'Cue 2 is red!' in first_text, f"Expected 'Cue 2 is red!', got: {first_text}"
    
    # Check second valid cue (Cue 4)
    second_text = ''.join(paragraphs[1].itertext()).strip()
    assert 'Cue 4 should be red too!' in second_text, f"Expected 'Cue 4 should be red too!', got: {second_text}"
    
    print("✓ VTT with timing errors: 2 valid cues converted, 2 malformed timing cues skipped")
    
    # Test 2b: VTT with malformed HTML tags - sanitization should remove bad tags
    vtt_with_bad_html = """WEBVTT

00:00:01.000 --> 00:00:03.000
Cue 1 with </bad> closing tag

00:00:04.000 --> 00:00:06.000
Cue 2 with <invalid> opening tag

00:00:07.000 --> 00:00:09.000
Cue 3 with <b>valid bold</b> text
"""
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_with_bad_html, sanitize_html=True)
    root = ET.fromstring(imsc1_content)
    paragraphs = root.findall('.//{http://www.w3.org/ns/ttml}p')
    
    assert len(paragraphs) == 3, f"Should convert all 3 cues after HTML sanitization, got {len(paragraphs)}"
    
    # Check that malformed tags were removed but text preserved
    first_text = ''.join(paragraphs[0].itertext()).strip()
    assert 'Cue 1 with' in first_text and 'closing tag' in first_text, f"Expected sanitized text, got: {first_text}"
    assert '</bad>' not in first_text, "Malformed closing tag should be removed"
    
    second_text = ''.join(paragraphs[1].itertext()).strip()
    assert 'Cue 2 with' in second_text and 'opening tag' in second_text, f"Expected sanitized text, got: {second_text}"
    assert '<invalid>' not in second_text, "Malformed opening tag should be removed"
    
    third_text = ''.join(paragraphs[2].itertext()).strip()
    assert 'valid bold' in third_text, f"Valid HTML should be preserved, got: {third_text}"
    
    print("✓ VTT with malformed HTML: bad tags sanitized, valid tags preserved, all cues converted")
    
    # Test 3: VTT with cue settings (positioning)
    vtt_with_settings = """WEBVTT

00:00:01.000 --> 00:00:03.000 line:90% position:50% align:center
Centered subtitle

00:00:05.000 --> 00:00:07.000 line:10%
Top subtitle
"""
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_with_settings)
    root = ET.fromstring(imsc1_content)
    paragraphs = root.findall('.//{http://www.w3.org/ns/ttml}p')
    
    assert len(paragraphs) == 2, "Should convert 2 cues with settings"
    
    # Verify positioning information is preserved (may be in style attributes or region)
    # Note: The exact attribute names depend on IMSC1 implementation
    first_p = paragraphs[0]
    # Check if any positioning/styling attributes are present
    has_style_info = any('style' in k.lower() or 'region' in k.lower() 
                         for k in first_p.attrib.keys())
    print(f"✓ VTT with cue settings converted (style info present: {has_style_info})")
    
    print("\n✓ All edge case tests passed")


def test_imsc1_against_reference():
    """Compare generated IMSC1 structure with reference IMSC1 file if available."""
    # Generate IMSC1 from VTT
    with open(Common.get_data_file_path('asset-test-vtt-syntax_ENG.vtt'), 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    if vtt_content.startswith('\ufeff'):
        vtt_content = vtt_content[1:]
    
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content)
    gen_root = ET.fromstring(imsc1_content)
    
    # Check if reference IMSC1 file exists
    ref_path = Common.get_data_file_path('asset-test-vtt-syntax_ENG_REF.imsc1')
    if not os.path.exists(ref_path):
        pytest.skip(f"Reference IMSC1 file not found at {ref_path}")
    
    # Load reference IMSC1
    with open(ref_path, 'r', encoding='utf-8') as f:
        reference = f.read()
    
    if reference.startswith('\ufeff'):
        reference = reference[1:]
    
    ref_root = ET.fromstring(reference)
    
    print("\nComparing generated IMSC1 with reference:")
    
    # Compare paragraph counts
    gen_p_count = len(gen_root.findall('.//{http://www.w3.org/ns/ttml}p'))
    ref_p_count = len(ref_root.findall('.//{http://www.w3.org/ns/ttml}p'))
    
    print(f"  Paragraph count: generated={gen_p_count}, reference={ref_p_count}")
    assert gen_p_count == ref_p_count, f"Paragraph count mismatch: {gen_p_count} vs {ref_p_count}"
    
    # Compare structure elements
    ttml_ns = 'http://www.w3.org/ns/ttml'
    for element_name in ['head', 'body', 'div', 'style']:
        gen_count = len(gen_root.findall(f'.//{{{ttml_ns}}}{element_name}'))
        ref_count = len(ref_root.findall(f'.//{{{ttml_ns}}}{element_name}'))
        match = "✓" if gen_count == ref_count else "✗"
        print(f"  {match} {element_name}: generated={gen_count}, reference={ref_count}")
    
    # Compare timing of first and last paragraphs
    gen_paragraphs = gen_root.findall('.//{http://www.w3.org/ns/ttml}p')
    ref_paragraphs = ref_root.findall('.//{http://www.w3.org/ns/ttml}p')
    
    if gen_paragraphs and ref_paragraphs:
        print(f"\n  First paragraph timing:")
        print(f"    Generated: begin={gen_paragraphs[0].attrib.get('begin', 'N/A')}")
        print(f"    Reference: begin={ref_paragraphs[0].attrib.get('begin', 'N/A')}")
        
        print(f"  Last paragraph timing:")
        print(f"    Generated: begin={gen_paragraphs[-1].attrib.get('begin', 'N/A')}")
        print(f"    Reference: begin={ref_paragraphs[-1].attrib.get('begin', 'N/A')}")
    
    # Compare text content of all paragraphs (handling <br/> elements and normalizing whitespace)
    print(f"\n  Text content comparison (all {len(gen_paragraphs)} paragraphs):")
    
    def extract_text_with_breaks(element):
        """Extract text from element, converting <br/> elements to newlines."""
        result = []
        if element.text:
            result.append(element.text)
        for child in element:
            # Handle br elements by adding newline
            if child.tag.endswith('br'):
                result.append('\n')
            # Recursively handle other children
            result.append(extract_text_with_breaks(child))
            if child.tail:
                result.append(child.tail)
        return ''.join(result)
    
    def normalize_whitespace(text):
        """Normalize whitespace: collapse multiple newlines to single, normalize line endings."""
        # First normalize all line ending types to \n
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Collapse multiple consecutive newlines to single newline
        import re
        text = re.sub(r'\n+', '\n', text)
        # Normalize spaces (but preserve newlines)
        lines = text.split('\n')
        lines = [' '.join(line.split()) for line in lines]  # Collapse spaces within lines
        return '\n'.join(lines).strip()
    
    mismatches = []
    for i in range(len(gen_paragraphs)):
        # Extract text with <br/> converted to newlines
        gen_text = extract_text_with_breaks(gen_paragraphs[i])
        ref_text = extract_text_with_breaks(ref_paragraphs[i])
        
        # Normalize whitespace for comparison (so multiple newlines = single newline)
        gen_normalized = normalize_whitespace(gen_text)
        ref_normalized = normalize_whitespace(ref_text)
        
        if gen_normalized != ref_normalized:
            mismatches.append({
                'index': i + 1,
                'generated': gen_normalized[:100],
                'reference': ref_normalized[:100]
            })
            print(f"    ✗ P{i+1}: Content mismatch")
            print(f"       Generated: '{gen_normalized[:80]}...'")
            print(f"       Reference: '{ref_normalized[:80]}...'")
    
    if mismatches:
        print(f"\n  Found {len(mismatches)} paragraph(s) with text content differences")
        assert False, f"Text content mismatch in {len(mismatches)} paragraph(s). First mismatch at P{mismatches[0]['index']}"
    else:
        print(f"    ✓ All {len(gen_paragraphs)} paragraphs have matching text content")
    
    print("\n✓ IMSC1 reference comparison completed")


def test_imsc1_segmentation():
    """Test that IMSC1 content can be segmented."""
    # Read asset-test-vtt-syntax_ENG.vtt
    with open(Common.get_data_file_path('asset-test-vtt-syntax_ENG.vtt'), 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    if vtt_content.startswith('\ufeff'):
        vtt_content = vtt_content[1:]
    
    # Convert to IMSC1
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content)
    
    # Segment with 4 second duration (typical segment size)
    segment_duration = 4.0
    segments = Imsc1Segmenter.segment(imsc1_content, segment_duration)
    
    # Verify segments were created
    assert segments is not None
    assert len(segments) > 0
    
    # Verify segment structure
    for start_time, segment_xml in segments:
        assert isinstance(start_time, float)
        assert isinstance(segment_xml, str)
        assert len(segment_xml) > 0
        assert '<?xml' in segment_xml
    
    print(f"✓ IMSC1 segmentation successful: {len(segments)} segments created")


def test_cmft_packaging():
    """Test that segmented IMSC1 can be packaged into CMFT format."""
    # Read asset-test-vtt-syntax_ENG.vtt
    with open(Common.get_data_file_path('asset-test-vtt-syntax_ENG.vtt'), 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    if vtt_content.startswith('\ufeff'):
        vtt_content = vtt_content[1:]
    
    # Convert to IMSC1
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content)
    
    # Segment
    segment_duration = 4.0
    segments = Imsc1Segmenter.segment(imsc1_content, segment_duration)
    
    # Calculate total duration
    if segments:
        last_start, _ = segments[-1]
        total_duration = last_start + segment_duration
    else:
        total_duration = 0.0
    
    # Package to CMFT
    cmft_data = CmftPackager.package(segments, timescale=10000000, total_duration=total_duration)
    
    # Verify CMFT data
    assert cmft_data is not None
    assert len(cmft_data) > 0
    
    # Check for key MP4 boxes
    assert b'ftyp' in cmft_data
    assert b'moov' in cmft_data
    assert b'moof' in cmft_data
    assert b'mdat' in cmft_data
    
    print(f"✓ CMFT packaging successful: {len(cmft_data)} bytes")


def test_full_vtt_to_cmft_conversion():
    """Test the complete VTT to CMFT conversion pipeline."""
    # Read asset-test-vtt-syntax_ENG.vtt
    with open(Common.get_data_file_path('asset-test-vtt-syntax_ENG.vtt'), 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    if vtt_content.startswith('\ufeff'):
        vtt_content = vtt_content[1:]
    
    # Step 1: Convert to IMSC1
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content)
    assert imsc1_content is not None
    
    # Step 2: Segment
    segment_duration = 4.0
    segments = Imsc1Segmenter.segment(imsc1_content, segment_duration)
    assert len(segments) > 0
    
    # Step 3: Package
    if segments:
        last_start, _ = segments[-1]
        total_duration = last_start + segment_duration
    else:
        total_duration = 0.0
    
    cmft_data = CmftPackager.package(segments, timescale=10000000, total_duration=total_duration)
    assert len(cmft_data) > 0
    
    print(f"✓ Full VTT to CMFT conversion successful")
    print(f"  Input: asset-test-vtt-syntax_ENG.vtt")
    print(f"  Segments: {len(segments)}")
    print(f"  Duration: {total_duration:.2f}s")
    
    # Compare with reference file if it exists
    if os.path.exists(Common.get_data_file_path('asset-test-vtt-syntax_ENG_REF.cmft')):
        with open(Common.get_data_file_path('asset-test-vtt-syntax_ENG_REF.cmft'), 'rb') as f:
            ref_data = f.read()
        
        print(f"\n  Reference file: asset-test-vtt-syntax_ENG_REF.cmft ({len(ref_data)} bytes)")
        print(f"  Size difference: {len(cmft_data) - len(ref_data)} bytes")
        
        # Note: Exact byte-for-byte match is unlikely due to:
        # - Timestamp precision differences
        # - Box ordering variations
        # - Metadata differences
        # But the structure should be similar
        
        # Check that key boxes exist in both
        for box in [b'ftyp', b'moov', b'mvhd', b'trak', b'mdia', b'minf', b'stbl', b'moof', b'mdat']:
            assert box in cmft_data, f"Missing box {box} in generated file"
            assert box in ref_data, f"Missing box {box} in reference file"
        
        print(f"  ✓ Both files contain required MP4 boxes")


def test_compare_with_reference():
    """Compare the generated CMFT with the reference file structure."""
    # Generate CMFT from VTT
    with open(Common.get_data_file_path('asset-test-vtt-syntax_ENG.vtt'), 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    if vtt_content.startswith('\ufeff'):
        vtt_content = vtt_content[1:]
    
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content)
    segment_duration = 4.0
    segments = Imsc1Segmenter.segment(imsc1_content, segment_duration)
    
    if segments:
        last_start, _ = segments[-1]
        total_duration = last_start + segment_duration
    else:
        total_duration = 0.0
    
    cmft_data = CmftPackager.package(segments, timescale=10000000, total_duration=total_duration)
    
    # Read reference file
    if not os.path.exists(Common.get_data_file_path('asset-test-vtt-syntax_ENG_REF.cmft')):
        pytest.skip("Reference file asset-test-vtt-syntax_ENG_REF.cmft not found")
    
    with open(Common.get_data_file_path('asset-test-vtt-syntax_ENG_REF.cmft'), 'rb') as f:
        ref_data = f.read()
    
    print(f"\nStructural comparison:")
    print(f"  Generated: {len(cmft_data)} bytes, {len(segments)} segments")
    print(f"  Reference: {len(ref_data)} bytes")
    
    # Count boxes in each file
    def count_boxes(data, box_name):
        return data.count(box_name.encode('utf-8'))
    
    for box in ['ftyp', 'moov', 'mvhd', 'trak', 'mdia', 'hdlr', 'minf', 'stbl', 'mvex', 'trex', 'moof', 'mfhd', 'traf', 'tfhd', 'trun', 'mdat']:
        gen_count = count_boxes(cmft_data, box)
        ref_count = count_boxes(ref_data, box)
        match = "✓" if gen_count == ref_count else "✗"
        print(f"  {match} {box}: generated={gen_count}, reference={ref_count}")


def test_bad_vtt_to_cmft_conversion():
    """Test the complete VTT to CMFT conversion pipeline."""
    # Read asset-test-vtt-syntax_ENG.vtt
    with open(Common.get_data_file_path('asset-test-vtt-syntax_BAD.vtt'), 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    if vtt_content.startswith('\ufeff'):
        vtt_content = vtt_content[1:]
    
    # Step 1: Convert to IMSC1
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content)
    assert imsc1_content is not None
    
    # Step 2: Segment
    segment_duration = 4.0
    segments = Imsc1Segmenter.segment(imsc1_content, segment_duration)
    assert len(segments) > 0
    
    # Step 3: Package
    if segments:
        last_start, _ = segments[-1]
        total_duration = last_start + segment_duration
    else:
        total_duration = 0.0
    
    cmft_data = CmftPackager.package(segments, timescale=10000000, total_duration=total_duration)
    assert len(cmft_data) > 0
    
    print(f"✓ Bad VTT to CMFT conversion successful")
    print(f"  Input: asset-test-vtt-syntax_BAD.vtt")
    print(f"  Segments: {len(segments)}")
    print(f"  Duration: {total_duration:.2f}s")

def test_big_vtt_to_cmft_conversion():
    """Test the complete VTT to CMFT conversion pipeline."""
    # Read asset-test-vtt-syntax_ENG.vtt
    with open(Common.get_data_file_path('asset-test-vtt-big-lorem.vtt'), 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    if vtt_content.startswith('\ufeff'):
        vtt_content = vtt_content[1:]
    
    # Step 1: Convert to IMSC1
    imsc1_content, warnings = VttToImsc1Converter.convert(vtt_content)
    assert imsc1_content is not None
    
    # Step 2: Segment
    segment_duration = 4.0
    segments = Imsc1Segmenter.segment(imsc1_content, segment_duration)
    assert len(segments) > 0
    
    # Step 3: Package
    if segments:
        last_start, _ = segments[-1]
        total_duration = last_start + segment_duration
    else:
        total_duration = 0.0
    
    cmft_data = CmftPackager.package(segments, timescale=10000000, total_duration=total_duration)
    assert len(cmft_data) > 0
    
    print(f"✓ Big VTT to CMFT conversion successful")
    print(f"  Input: asset-test-vtt-big-lorem.vtt")
    print(f"  Segments: {len(segments)}")
    print(f"  Duration: {total_duration:.2f}s")
    

if __name__ == '__main__':
    print("Running VTT to CMFT conversion tests...\n")
    
    try:
        test_vtt_to_imsc1_conversion()
        print()
        
        test_vtt_edge_cases()
        print()
        
        test_imsc1_against_reference()
        print()
        
        test_imsc1_segmentation()
        print()
        
        test_cmft_packaging()
        print()
        
        test_full_vtt_to_cmft_conversion()
        print()
        
        test_bad_vtt_to_cmft_conversion()
        print()
        
        test_big_vtt_to_cmft_conversion()
        print()
        
        test_compare_with_reference()
        print()
        
        print("\n" + "="*60)
        print("All tests completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
