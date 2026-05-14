from enum import Enum

class NodeType(str, Enum):
    PRACTITIONER = "Practitioner"
    SPECIALISM = "Specialism"
    SEEK = "Seek"
    MATERIAL = "Material"
    VENUE = "Venue"

class EdgeType(str, Enum):
     HAS_SPECIALISM = "HAS_SPECIALISM"      
     CAN_SUPPORT = "CAN_SUPPORT"
     HAS_SEEK = "HAS_SEEK"                 
     AT_VENUE = "AT_VENUE"                
     FOUND_MATERIAL = "FOUND_MATERIAL"     
     TREATS = "TREATS"  
