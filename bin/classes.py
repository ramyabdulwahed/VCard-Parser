import ctypes
from ctypes import *
class Property(Structure):
    _fields_ = [
        ("name", c_char_p),
        ("group", c_char_p),
        ("parameters", c_void_p),  # Assuming List is a pointer
        ("values", c_void_p)  # Assuming List is a pointer
    ]

class DateTime(Structure):
    _fields_ = [
        ("date", c_char_p),
        ("time", c_char_p),
        ("isText", c_bool),
        ("text", c_char_p),
        ("UTC", c_bool)
    ]

class Card(Structure):
    _fields_ = [
        ("fn", POINTER(Property)),  # Pointer to Property struct
        ("birthday", POINTER(DateTime)),  # Pointer to DateTime struct
        ("anniversary", POINTER(DateTime)),  # Pointer to DateTime struct
        ("optionalProperties", c_void_p)  # Placeholder for List
    ]