from bisect import bisect_left
from typing import List, Tuple
from xml.etree import ElementTree as ET

from external_asset_ism_ismc_generation_tool.common.logger.i_logger import ILogger
from external_asset_ism_ismc_generation_tool.common.logger.logger import Logger


class Imsc1Segmenter:
    """Segments IMSC1 content into fixed-duration chunks."""
    
    __logger: ILogger = Logger("Imsc1Segmenter")

    @classmethod
    def redefine_logger(cls, logger: ILogger):
        cls.__logger = logger

    @staticmethod
    def segment(imsc1_content: str, segment_duration: float) -> List[Tuple[float, str]]:
        """
        Segment IMSC1 content into fixed-duration chunks.
        
        Args:
            imsc1_content: String containing IMSC1 (TTML) XML content
            segment_duration: Duration of each segment in seconds (fixed value, typically 4.0)
            
        Returns:
            List of tuples containing (start_time, segment_xml_string)
        """
        Imsc1Segmenter.__logger.info(f"Segmenting IMSC1 with segment duration: {segment_duration}s")
        
        try:
            # Parse the IMSC1 XML
            root = ET.fromstring(imsc1_content)
            
            # Define namespaces
            namespaces = {
                'tt': 'http://www.w3.org/ns/ttml',
                'tts': 'http://www.w3.org/ns/ttml#styling',
                'ttm': 'http://www.w3.org/ns/ttml#metadata'
            }
            
            # Find all <p> elements (subtitle cues)
            body = root.find('.//tt:body', namespaces)
            if body is None:
                # Try without namespace
                body = root.find('.//body')
            
            if body is None:
                Imsc1Segmenter.__logger.error("No body element found in IMSC1 content")
                raise ValueError("No body element found in IMSC1 content")
            
            div = body.find('.//tt:div', namespaces)
            if div is None:
                div = body.find('.//div')
            
            if div is None:
                Imsc1Segmenter.__logger.error("No div element found in IMSC1 content")
                raise ValueError("No div element found in IMSC1 content")
            
            # Get all <p> elements
            p_elements = div.findall('.//tt:p', namespaces)
            if not p_elements:
                p_elements = div.findall('.//p')
            
            if not p_elements:
                Imsc1Segmenter.__logger.warning("No subtitle cues found in IMSC1 content")
                return []
            
            # Group cues by segments
            segments = []
            current_segment_start = 0.0
            current_segment_end = float(segment_duration)
            
            # Pre-parse all cue times once (avoids re-parsing inside the segment loop)
            cue_data = []
            for p_elem in p_elements:
                begin_time = Imsc1Segmenter.__parse_time(p_elem.get('begin', ''))
                end_time = Imsc1Segmenter.__parse_time(p_elem.get('end', ''))
                cue_data.append((begin_time, end_time, p_elem))
            
            # Sort by begin time (should already be ordered, but makes bisect safe)
            cue_data.sort(key=lambda c: c[0])
            
            # Separate lists for binary search
            begin_times = [c[0] for c in cue_data]
            end_times = [c[1] for c in cue_data]
            
            # Get total duration from the last cue end time
            total_duration = max(end_times) if end_times else 0.0
            
            Imsc1Segmenter.__logger.info(f"Total subtitle duration: {total_duration}s")
            
            # Create segments using binary search to find overlapping cues
            while current_segment_start < total_duration:
                segment_cues = []
                
                # A cue overlaps the segment [seg_start, seg_end) when:
                #   cue.begin < seg_end  AND  cue.end > seg_start
                #
                # Upper bound on begin_times: first index where begin >= seg_end
                # → all cues before this index have begin < seg_end.
                # We then filter by end_time > seg_start inside the loop,
                # since end_times are NOT sorted (cues may overlap).
                upper = bisect_left(begin_times, current_segment_end)
                
                for begin_time, end_time, p_elem in cue_data[:upper]:
                    if end_time > current_segment_start:
                        # Create a copy of the cue element to modify its timing
                        cue_copy = ET.Element(p_elem.tag, attrib=p_elem.attrib.copy())
                        cue_copy.text = p_elem.text
                        cue_copy.tail = p_elem.tail
                        
                        # Copy all child elements
                        for child in p_elem:
                            cue_copy.append(child)
                        
                        # Adjust timing to fit within segment boundaries
                        adjusted_begin = max(begin_time, current_segment_start)
                        adjusted_end = min(end_time, current_segment_end)
                        
                        # Format times back to HH:MM:SS.mmm format
                        cue_copy.set('begin', Imsc1Segmenter.__format_time(adjusted_begin))
                        cue_copy.set('end', Imsc1Segmenter.__format_time(adjusted_end))
                        
                        segment_cues.append(cue_copy)
                
                # Create segment XML (always create segment, even if empty, to maintain timing alignment)
                segment_xml = Imsc1Segmenter.__create_segment_xml(root, segment_cues, namespaces)
                segments.append((current_segment_start, segment_xml))
                if segment_cues:
                    Imsc1Segmenter.__logger.info(f"Created segment at {current_segment_start}s with {len(segment_cues)} cues")
                # Note: Empty segments are still created for timing alignment, but not logged to reduce noise
                
                # Move to next segment
                current_segment_start = current_segment_end
                current_segment_end += segment_duration
            
            Imsc1Segmenter.__logger.info(f"Created {len(segments)} segments")
            return segments
            
        except ET.ParseError as e:
            error_msg = f"Failed to parse IMSC1 XML: {e}"
            Imsc1Segmenter.__logger.error(error_msg)
            Imsc1Segmenter.__logger.error("Check that the IMSC1 content is valid XML")
            raise ValueError(f"Failed to segment IMSC1: {error_msg}")
            
        except ValueError as e:
            # Re-raise ValueError (including our own validation errors)
            if "Failed to segment IMSC1" in str(e):
                raise
            error_msg = f"IMSC1 segmentation validation error: {e}"
            Imsc1Segmenter.__logger.error(error_msg)
            raise ValueError(f"Failed to segment IMSC1: {error_msg}")
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = f"Unexpected error segmenting IMSC1 ({error_type}): {e}"
            Imsc1Segmenter.__logger.error(error_msg)
            Imsc1Segmenter.__logger.error(f"Segment duration: {segment_duration}s")
            raise ValueError(f"Failed to segment IMSC1: {error_msg}")

    @staticmethod
    def __parse_time(time_str: str) -> float:
        """
        Parse TTML time format (HH:MM:SS.mmm) to seconds.
        
        Args:
            time_str: Time string in format HH:MM:SS.mmm
            
        Returns:
            Time in seconds as float
        """
        if not time_str:
            return 0.0
        
        try:
            # Parse HH:MM:SS.mmm format
            time_parts = time_str.split(':')
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds_parts = time_parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            return total_seconds
        except Exception as e:
            Imsc1Segmenter.__logger.error(f"Error parsing time '{time_str}': {e}")
            return 0.0

    @staticmethod
    def __format_time(time_seconds: float) -> str:
        """
        Format time in seconds to TTML time format (HH:MM:SS.mmm).
        
        Args:
            time_seconds: Time in seconds as float
            
        Returns:
            Time string in format HH:MM:SS.mmm
        """
        hours = int(time_seconds // 3600)
        remaining = time_seconds % 3600
        minutes = int(remaining // 60)
        seconds = remaining % 60
        
        # Format with milliseconds (3 decimal places)
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    @staticmethod
    def __create_segment_xml(root: ET.Element, cues: List[ET.Element], namespaces: dict) -> str:
        """
        Create a new IMSC1 XML document for a segment.
        
        Args:
            root: Original IMSC1 root element
            cues: List of <p> elements to include in this segment
            namespaces: XML namespaces
            
        Returns:
            XML string for the segment
        """
        # Create a new IMSC1 document structure
        # Register namespaces
        for prefix, uri in namespaces.items():
            ET.register_namespace(prefix, uri)
        ET.register_namespace('', 'http://www.w3.org/ns/ttml')
        
        # Create new root element with same attributes
        new_root = ET.Element(root.tag, attrib=root.attrib)
        
        # Collect regions used in this segment's cues
        used_regions = set()
        for cue in cues:
            region = cue.get('region')
            if region:
                used_regions.add(region)
        
        # Copy head element with filtered regions
        head = root.find('.//tt:head', namespaces)
        if head is None:
            head = root.find('.//head')
        if head is not None:
            new_head = ET.SubElement(new_root, head.tag, attrib=head.attrib)
            # Copy children of head, filtering layout regions
            for child in head:
                if 'layout' in child.tag.lower():
                    # This is a layout element, need to filter regions
                    new_layout = ET.SubElement(new_head, child.tag, attrib=child.attrib)
                    # Copy only the regions that are used in this segment
                    for region in child:
                        if 'region' in region.tag.lower():
                            region_id = region.get('{http://www.w3.org/XML/1998/namespace}id')
                            if region_id in used_regions:
                                new_layout.append(region)
                        else:
                            # Not a region element, copy as-is
                            new_layout.append(region)
                else:
                    # Not a layout element, copy as-is
                    new_head.append(child)
        else:
            # Create empty head
            ET.SubElement(new_root, '{http://www.w3.org/ns/ttml}head')
        
        # Create body element
        body = root.find('.//tt:body', namespaces)
        if body is None:
            body = root.find('.//body')
        
        body_attrib = body.attrib if body is not None else {}
        new_body = ET.SubElement(new_root, '{http://www.w3.org/ns/ttml}body', attrib=body_attrib)
        
        # Create div element
        div = body.find('.//tt:div', namespaces) if body is not None else None
        if div is None and body is not None:
            div = body.find('.//div')
        
        div_attrib = div.attrib if div is not None else {}
        new_div = ET.SubElement(new_body, '{http://www.w3.org/ns/ttml}div', attrib=div_attrib)
        
        # Add cues to div
        for cue in cues:
            new_div.append(cue)
        
        # Convert to string
        xml_str = ET.tostring(new_root, encoding='utf-8', xml_declaration=True).decode('utf-8')
        return xml_str
