from __future__ import annotations
import attr

from attr import define
from typing import Optional, List, Dict, Tuple, List
from numbers import Number

from enum import Enum

from reflexgenerator.generator.xref import UidReference


# ---------------------------------------------------------------------------- #
#                            Special types and Enums                           #
# ---------------------------------------------------------------------------- #

PayloadType = Enum("PayloadType", [
    "U8", "U16", "U32", "U64",
    "S8", "S16", "S32", "S64",
    "Float"])


def _payloadType_converter(value: PayloadType | str) -> PayloadType:
    if isinstance(value, str):
        return PayloadType[value]
    if isinstance(value, PayloadType):
        return value
    raise TypeError("Must be PayloadType or str.")


RegisterType = Enum("RegisterType", [
    "NONE", "Command", "Event", "Both"
])


def _registerType_converter(
        value: RegisterType | str | List[RegisterType | str]
        ) -> RegisterType:
    if isinstance(value, str):
        return [RegisterType[value]]
    if isinstance(value, RegisterType):
        return [value]
    if isinstance(value, list):
        return [_registerType_converter(_value) for _value in value]
    raise TypeError("Must be RegisterType or str.")


VisibilityType = Enum("VisibilityType", [
    "Public", "Private"
])


def _visibilityType_converter(
        value: VisibilityType | str
        ) -> VisibilityType:
    if isinstance(value, str):
        return VisibilityType[value]
    if isinstance(value, VisibilityType):
        return value
    raise TypeError("Must be VisibilityType or str.")


MaskCategory = Enum("MaskType", [
    "BitMask", "GroupMask"
])


def _maskCategory_converter(value: MaskCategory | str) -> MaskCategory:
    if isinstance(value, str):
        return MaskCategory[value]
    if isinstance(value, MaskCategory):
        return value
    raise TypeError("Must be MaskType or str.")


# ---------------------------------------------------------------------------- #
#                                Device metadata                               #
# ---------------------------------------------------------------------------- #


@define
class Metadata:
    device = attr.ib(type=str)
    whoAmI = attr.ib(type=int)
    firmwareVersion = attr.ib(default=None, type=Optional[str])
    hardwareTargets = attr.ib(default=None, type=Optional[str])
    architecture = attr.ib(default=None, type=Optional[str])
    uid = attr.ib(default=None, type=Optional[UidReference])

    def __attrs_post_init__(self):
        if self.uid is None:
            self.uid = UidReference(self)

    @property
    def name(self) -> str:
        return f"{self.device}_{self.whoAmI}"

    def to_dict(self) -> Dict[str, any]:
        return attr.asdict(self, recurse=False)


# ---------------------------------------------------------------------------- #
#                                     Masks                                    #
# ---------------------------------------------------------------------------- #


_MASKS = {}


@define
class BitOrValue:
    name = attr.ib(default=None, type=Optional[str], converter=str)
    value = attr.ib(default=None, type=Optional[int], converter=hex)
    description = attr.ib(default=None, type=Optional[str], converter=str)
    uid = attr.ib(default=None, type=Optional[UidReference])

    def __attrs_post_init__(self):
        if self.uid is None:
            self.uid = UidReference(self)

    @classmethod
    def parse(self,
              value: Tuple[str, Dict[Number | str, Optional[str]]]
              ) -> BitOrValue:
        _name = value[0]
        _value = list(value[1].keys())[0]
        try:
            _description = value[1]["description"]
        except KeyError:
            _description = None
        return BitOrValue(
            name=_name,
            value=_value,
            description=_description)


def _make_bitorvalue_array(
        value: Optional[Dict[str, int]]
        ) -> Optional[List[BitOrValue]]:
    if value is None:
        return None
    if isinstance(value, dict):
        return [BitOrValue.parse(bit) for bit in value.items()]


@define
class Mask:
    name = attr.ib(type=str, converter=str)
    description = attr.ib(default=None,
                          type=Optional[str], converter=str)
    value = attr.ib(default=None,
                    type=Optional[List[BitOrValue]],
                    converter=_make_bitorvalue_array)
    bits = attr.ib(default=None,
                   type=Optional[List[BitOrValue]],
                   converter=_make_bitorvalue_array)
    maskCategory = attr.ib(default=None,
                           type=Optional[MaskCategory],
                           converter=_maskCategory_converter)
    uid = attr.ib(default=None, type=Optional[UidReference])

    def __attrs_post_init__(self):
        _MASKS.update({self.name: self})
        if self.uid is None:
            self.uid = UidReference(self)

    def to_dict(self) -> Dict[str, any]:
        return attr.asdict(self, recurse=False)

    @classmethod
    def from_json(self,
                  json_object: Tuple[str, Dict[str, any]],
                  infer_maskCategory=True,
                  maskCategory: Optional[MaskCategory] = None) -> Mask:

        _name = json_object[0]
        if infer_maskCategory:
            if 'bits' in json_object[1]:
                _mask_cat = MaskCategory.BitMask
            elif 'values' in json_object[1]:
                _mask_cat = MaskCategory.GroupMask
            else:
                raise KeyError("Could not infer MaskCategory.\
                                Try to manually assign it.")
            return Mask(name=_name,
                        maskCategory=_mask_cat,
                        **json_object[1])
        else:
            if maskCategory:
                return Mask(name=_name,
                            maskCategory=maskCategory,
                            **json_object[1])
            else:
                raise ValueError("maskCategory cannot be 'None' \
                                 if 'infer_maskCategory' is False")


def get_mask(value: Optional[str | list[str]]) -> Optional[list[Mask]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [_get_mask_helper(_mask) for _mask in value]
    if isinstance(value, str):
        return [_get_mask_helper(value)]
    raise ValueError("Invalid input format.")


def _get_mask_helper(value: str) -> Mask:
    if value in list(_MASKS.keys()):
        return (_MASKS[value])
    else:
        raise KeyError("Specified mask has not been defined.")


# ---------------------------------------------------------------------------- #
#                                Registers                                     #
# ---------------------------------------------------------------------------- #


@define
class PayloadMember:
    name = attr.ib(type=str)
    mask = attr.ib(default=None, type=Optional[int],
                   converter=lambda value: int(value)
                   if value is not None else None)
    offset = attr.ib(default=1, type=Optional[int], converter=int)
    maskType = attr.ib(default=None,
                       type=Optional[List[Mask]], converter=get_mask)
    description = attr.ib(default=None, type=Optional[str], converter=str)
    converter = attr.ib(default=None, type=Optional[bool])
    defaultValue = attr.ib(default=None, type=Optional[Number])
    maxValue = attr.ib(default=None, type=Optional[Number])
    minValue = attr.ib(default=None, type=Optional[Number])
    interfaceType = attr.ib(default=None, type=Optional[str])
    uid = attr.ib(default=None, type=Optional[UidReference])

    def __attrs_post_init__(self):
        if self.uid is None:
            self.uid = UidReference(self)

    def to_dict(self) -> Dict[str, any]:
        return attr.asdict(self, recurse=False, )

    @classmethod
    def from_json(self,
                  json_object: Tuple[str, Dict[str, any]]) -> PayloadMember:
        _name = json_object[0]
        return PayloadMember(name=_name, **json_object[1])


def _payloadSpec_parser(
        value: Optional[List[PayloadMember] | PayloadMember | Dict[str, any]]
        ) -> Optional[List[PayloadMember]]:
    if value is None:
        return None
    if isinstance(value, PayloadMember):
        return [value]
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [PayloadMember.from_json(s) for s in value.items()]
    print(value, type(value))
    raise TypeError("Unexpected input type.")


@define
class Register:
    name = attr.ib(type=str)
    address = attr.ib(type=int, converter=int)
    payloadType = attr.ib(type=PayloadType | str,
                          converter=_payloadType_converter)
    payloadLength = attr.ib(default=1, type=int, converter=int)
    registerType = attr.ib(default=RegisterType.NONE,
                           type=str, converter=_registerType_converter)
    payloadSpec = attr.ib(default=None,
                          type=Optional[Dict[str, any]],
                          converter=_payloadSpec_parser)
    maskType = attr.ib(default=None,
                       type=Optional[List[Mask]], converter=get_mask)
    description = attr.ib(default=None, type=Optional[str], converter=str)
    converter = attr.ib(default=None, type=Optional[bool])
    defaultValue = attr.ib(default=None, type=Optional[Number])
    maxValue = attr.ib(default=None, type=Optional[Number])
    minValue = attr.ib(default=None, type=Optional[Number])
    interfaceType = attr.ib(default=None, type=Optional[str])
    visibility = attr.ib(default=VisibilityType.Public,
                         type=str, converter=_visibilityType_converter)
    group = attr.ib(default=None, type=Optional[str], converter=str)
    uid = attr.ib(default=None, type=Optional[UidReference])

    def __attrs_post_init__(self):
        if self.uid is None:
            self.uid = UidReference(self)

    def to_dict(self) -> Dict[str, any]:
        return attr.asdict(self, recurse=False, )

    @classmethod
    def from_json(self,
                  json_object: Tuple[str, Dict[str, any]]) -> Register:

        _name = json_object[0]
        return Register(name=_name, **json_object[1])

    def render_uref(self, label: Optional[str] = None) -> str:
        return self.uid.render_reference(label)

    def render_pointer(self, label: Optional[str] = None) -> str:
        return self.uid.render_pointer(label)


# ---------------------------------------------------------------------------- #
#                                      PinMapping                              #
# ---------------------------------------------------------------------------- #
DirectionType = Enum("DirectionType", ["input", "output"])


def _directionType_converter(
        value: DirectionType | str
        ) -> DirectionType:
    if isinstance(value, str):
        return DirectionType[value]
    if isinstance(value, DirectionType):
        return value
    raise TypeError("Must be DirectionType or str.")


InputPinModeType = Enum(
    "InputPinModeType", ["pullup", "pulldown", "tristate", "busholder"])


def _inputPinModeType_converter(
        value: InputPinModeType | str
        ) -> InputPinModeType:
    if isinstance(value, str):
        return InputPinModeType[value]
    if isinstance(value, InputPinModeType):
        return value
    raise TypeError("Must be InputPinModeType or str.")


TriggerModeType = Enum(
    "TriggerModeType", ["none", "rising", "falling", "toggle", "low"])


def _triggerModeType_converter(
        value: TriggerModeType | str
        ) -> TriggerModeType:
    if isinstance(value, str):
        return TriggerModeType[value]
    if isinstance(value, TriggerModeType):
        return value
    raise TypeError("Must be TriggerModeType or str.")


InterruptPriorityType = Enum(
    "InterruptPriorityType", ["off", "low", "medium", "high"])


def _interruptPriorityType_converter(
        value: InterruptPriorityType | str
        ) -> InterruptPriorityType:
    if isinstance(value, str):
        return InterruptPriorityType[value]
    if isinstance(value, InterruptPriorityType):
        return value
    raise TypeError("Must be InterruptPriorityType or str.")


OutputPinModeType = Enum(
    "OutputPinModeType", ["wiredOr", "wiredAnd", "wiredOrPull", "wiredAndPull"])


def _outputPinModeType_converter(
        value: OutputPinModeType | str
        ) -> OutputPinModeType:
    if isinstance(value, str):
        return OutputPinModeType[value]
    if isinstance(value, OutputPinModeType):
        return value
    raise TypeError("Must be OutputPinModeType or str.")


InitialStateType = Enum("initialStateType", ["low", "high"])


def _initialStateType_converter(
        value: InitialStateType | str
        ) -> InitialStateType:
    if isinstance(value, str):
        return InitialStateType[value]
    if isinstance(value, InitialStateType):
        return value
    raise TypeError("Must be InitialStateType or str.")


def PinMap(kwargs) -> InputPin | OutputPin:
    if "direction" not in kwargs:
        raise KeyError("Key 'direction' not found.")
    if kwargs["direction"] == "input":
        return InputPin(**kwargs)
    elif kwargs["direction"] == "output":
        return OutputPin(**kwargs)
    else:
        raise ValueError("Invalid value for 'direction'.")


def PinMap_from_json(
        json_object: Tuple[str, Dict[str, any]]
        ) -> InputPin | OutputPin:
    if "direction" not in json_object[1]:
        raise KeyError("Key 'direction' not found.")
    if json_object[1]["direction"] == "input":
        return InputPin.from_json(json_object)
    elif json_object[1]["direction"] == "output":
        return OutputPin.from_json(json_object)
    else:
        raise ValueError("Invalid value for 'direction'.")


@define
class InputPin:
    name = attr.ib(type=str)
    port = attr.ib(type=str)
    pinNumber = attr.ib(type=int, converter=int)
    direction = attr.ib(type=str, converter=_directionType_converter)
    pinMode = attr.ib(type=str, converter=_inputPinModeType_converter)
    triggerMode = attr.ib(type=str, converter=_triggerModeType_converter)
    interruptPriority = attr.ib(type=str, converter=_interruptPriorityType_converter)
    interruptNumber = attr.ib(type=int, converter=int)
    description = attr.ib(default=None, type=Optional[str], converter=str)
    uid = attr.ib(default=None, type=Optional[UidReference])

    def __attrs_post_init__(self):
        if self.uid is None:
            self.uid = UidReference(self)

    def to_dict(self):
        return attr.asdict(self, recurse=True)

    @classmethod
    def from_json(self,
                  json_object: Tuple[str, Dict[str, any]]) -> InputPin:

        _name = json_object[0]
        return InputPin(name=_name, **json_object[1])


@define
class OutputPin:
    name = attr.ib(type=str)
    port = attr.ib(type=str)
    pinNumber = attr.ib(type=int, converter=int)
    direction = attr.ib(type=str, converter=_directionType_converter)
    allowRead = attr.ib(type=bool, converter=bool)
    pinMode = attr.ib(type=str, converter=_outputPinModeType_converter)
    initialState = attr.ib(type=int, converter=_initialStateType_converter)
    invert = attr.ib(type=bool, converter=bool)
    description = attr.ib(default=None, type=Optional[str], converter=str)
    uid = attr.ib(default=None, type=Optional[UidReference])

    def __attrs_post_init__(self):
        if self.uid is None:
            self.uid = UidReference(self)

    def to_dict(self):
        return attr.asdict(self, recurse=True)

    @classmethod
    def from_json(self,
                  json_object: Tuple[str, Dict[str, any]]) -> OutputPin:

        _name = json_object[0]
        return OutputPin(name=_name, **json_object[1])
# ---------------------------------------------------------------------------- #
#                               Collection types                               #
# ---------------------------------------------------------------------------- #


_COLLECTION_TYPE = List[Register] | List[Mask] | List[Metadata] | List[InputPin | OutputPin]
_ELEMENT_TYPE = Register | Mask | Metadata | InputPin | OutputPin


class Collection:
    "Parent class that represents a collection of HarpElements"
    def __init__(
        self,
        element_array: Optional[_COLLECTION_TYPE],
        ) -> None:

        self.elements = []
        if element_array:
            self.from_array(element_array)

    def __iter__(self):
        return iter(self.elements)

    def from_array(self, arr: Optional[_COLLECTION_TYPE]) -> None:
        if len(arr) < 1:
            raise ValueError("List can't be empty!")
        for element in arr:
            self.append(element)

    def append(self, element: _ELEMENT_TYPE) -> None:
        self.elements.append(element)

    def insert(self, idx: int, element: _ELEMENT_TYPE) -> None:
        self.elements.insert(idx, element)

    def pop(self, idx: Optional[int]) -> None:
        self.elements.pop(idx)

    def __getitem__(self, index):
        return self.elements[index]