import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class DataContainer:
    """
    Generic Data Container with key-like attribute access.

    dataclasses import: creates automatically __init__()-method with data and filepath
    (see https://docs.python.org/3/library/dataclasses.html)
    customized field function: init=False --> field data of the class DataContainer() is delated
    (https://hackthedeveloper.com/python-data-class-field/)
    """

    data: pd.DataFrame = field(init=False, default=pd.DataFrame)
    domain: str = field(init=False, default=None)
    _temporary_attr_storage: list = field(init=False, default_factory=list)
    filepath: str

    def set_attribute(self, name: str, value) -> None:
        """
        Method to set attributes from outside class to instance of object.
        :param name: Sets name of added attribute
        :param value: Sets value of added attribute
        """
        if not hasattr(self, name):
            self.__setitem__(name, value)

    def __repr__(self) -> repr:
        """
        Override representation of object.
        :return: repr
        """
        if self.domain is None:
            return repr(f"Content from {os.path.basename(self.filepath)}")
        else:
            return repr(f"Content from {os.path.basename(self.filepath)}; Sheet: {self.domain}")

    def __getitem__(self, item):
        """
        Allows dict-like attribute access to access attributes with square brackets.
        :param item: obj attribute of name == item
        :return: obj attribute name == item
        (https://www.geeksforgeeks.org/__getitem__-in-python/)
        """
        return self.__getattribute__(item)

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __getattr__(self, item):
        return self.__getattribute__(item)

    def __delitem__(self, key):
        self.__delattr__(key)

    def add_temporary_attr(self, attribute_name):
        self._temporary_attr_storage.append(attribute_name)

    def clear_container(self):
        self._temporary_attr_storage.clear()

    def check_attr(self, attribute_name, temporary: bool = False):
        if (temporary is True) and (not hasattr(self, attribute_name)):
            self.add_temporary_attr(attribute_name)

    def update_domain_name(self, value):
        self.domain = value


class InterfaceWorldData(DataContainer, ABC):
    """
    Abstract class for WorldDataCollector as interface.
    """

    def __init__(self, filepath):
        super().__init__(filepath)
        self.periods_forecast = {}
        pass

    @property
    @abstractmethod
    def Regions(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def Commodities(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def Demand(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def Supply(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def RecyclingS(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def Forest(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ManufactureCost(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ManufactureCoefficients(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def TransportationImport(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def TransportationExport(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ExogChangeSupply(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ExogChangeDemand(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ExogChangeForest(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ExogChangeTradeImport(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ExogChangeTradeExport(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ExogChangeManufactureCost(self) -> DataContainer:
        pass

    @property
    @abstractmethod
    def ExogChangeManufactureCoefficients(self) -> DataContainer:
        pass

    def __repr__(self):
        return repr(f"Generic Data Collector")


class WorldDataCollector(InterfaceWorldData):
    """
    Class that implements InterfaceWorldData.
    """

    def __init__(self, filepath):
        super().__init__(filepath)
        self._Demand = DataContainer(filepath)
        self._Regions = DataContainer(filepath)
        self._Commodities = DataContainer(filepath)
        self._Supply = DataContainer(filepath)
        self._RecyclingS = DataContainer(filepath)
        self._Forest = DataContainer(filepath)
        self._ManufactureCost = DataContainer(filepath)
        self._ManufactureCoefficients = DataContainer(filepath)
        self._TransportationImport = DataContainer(filepath)
        self._TransportationExport = DataContainer(filepath)
        self._ExogChangeSupply = DataContainer(filepath)
        self._ExogChangeDemand = DataContainer(filepath)
        self._ExogChangeForest = DataContainer(filepath)
        self._ExogChangeTradeImport = DataContainer(filepath)
        self._ExogChangeTradeExport = DataContainer(filepath)
        self._ExogChangeManufactureCost = DataContainer(filepath)
        self._ExogChangeManufactureCoefficients = DataContainer(filepath)

    @property
    def Demand(self) -> DataContainer:
        return self._Demand

    @Demand.setter
    def Demand(self, value):
        self._Demand = value

    @property
    def Regions(self) -> DataContainer:
        return self._Regions

    @Regions.setter
    def Regions(self, value):
        self._Regions = value

    @property
    def Supply(self) -> DataContainer:
        return self._Supply

    @Supply.setter
    def Supply(self, value):
        self._Supply = value

    @property
    def RecyclingS(self) -> DataContainer:
        return self._RecyclingS

    @RecyclingS.setter
    def RecyclingS(self, value):
        self._RecyclingS = value

    @property
    def Commodities(self) -> DataContainer:
        return self._Commodities

    @Commodities.setter
    def Commodities(self, value):
        self._Commodities = value

    @property
    def Forest(self) -> DataContainer:
        return self._Forest

    @Forest.setter
    def Forest(self, value):
        self._Forest = value

    @property
    def ManufactureCost(self) -> DataContainer:
        return self._ManufactureCost

    @ManufactureCost.setter
    def ManufactureCost(self, value):
        self._ManufactureCost = value

    @property
    def ManufactureCoefficients(self) -> DataContainer:
        return self._ManufactureCoefficients

    @ManufactureCoefficients.setter
    def ManufactureCoefficients(self, value):
        self._ManufactureCoefficients = value

    @property
    def TransportationImport(self) -> DataContainer:
        return self._TransportationImport

    @TransportationImport.setter
    def TransportationImport(self, value):
        self._TransportationImport = value

    @property
    def TransportationExport(self) -> DataContainer:
        return self._TransportationExport

    @TransportationExport.setter
    def TransportationExport(self, value):
        self._TransportationExport = value

    @property
    def ExogChangeSupply(self) -> DataContainer:
        return self._ExogChangeSupply

    @ExogChangeSupply.setter
    def ExogChangeSupply(self, value):
        self._ExogChangeSupply = value

    @property
    def ExogChangeDemand(self) -> DataContainer:
        return self._ExogChangeDemand

    @ExogChangeDemand.setter
    def ExogChangeDemand(self, value):
        self._ExogChangeDemand = value

    @property
    def ExogChangeForest(self) -> DataContainer:
        return self._ExogChangeForest

    @ExogChangeForest.setter
    def ExogChangeForest(self, value):
        self._ExogChangeForest = value

    @property
    def ExogChangeTradeImport(self) -> DataContainer:
        return self._ExogChangeTradeImport

    @ExogChangeTradeImport.setter
    def ExogChangeTradeImport(self, value):
        self._ExogChangeTradeImport = value

    @property
    def ExogChangeTradeExport(self) -> DataContainer:
        return self._ExogChangeTradeExport

    @ExogChangeTradeExport.setter
    def ExogChangeTradeExport(self, value):
        self._ExogChangeTradeExport = value

    @property
    def ExogChangeManufactureCost(self) -> DataContainer:
        return self._ExogChangeManufactureCost

    @ExogChangeManufactureCost.setter
    def ExogChangeManufactureCost(self, value):
        self._ExogChangeManufactureCost = value

    @property
    def ExogChangeManufactureCoefficients(self) -> DataContainer:
        return self._ExogChangeManufactureCoefficients

    @ExogChangeManufactureCoefficients.setter
    def ExogChangeManufactureCoefficients(self, value):
        self._ExogChangeManufactureCoefficients = value


class AdditionalInformation(DataContainer):

    def __init__(self, filepath):
        super().__init__(filepath)
        self._Country = DataContainer(filepath)
        self._Commodity = DataContainer(filepath)
        self._Element = DataContainer(filepath)
        self._CommodityList = DataContainer(filepath)
        self._Carbon = DataContainer(filepath)
        self._CarbonConstraint = DataContainer(filepath)
        self._CarbonShadowPrice = DataContainer(filepath)

    @property
    def Country(self) -> DataContainer:
        return self._Country

    @Country.setter
    def Country(self, value):
        self._Country = value

    @property
    def Commodity(self) -> DataContainer:
        return self._Commodity

    @Commodity.setter
    def Commodity(self, value):
        self._Commodity = value

    @property
    def Element(self) -> DataContainer:
        return self._Element

    @Element.setter
    def Element(self, value):
        self._Element = value

    @property
    def CommodityList(self) -> DataContainer:
        return self._CommodityList

    @CommodityList.setter
    def CommodityList(self, value):
        self._CommodityList = value

    @property
    def CarbonConstraint(self) -> DataContainer:
        return self._CarbonConstraint

    @CarbonConstraint.setter
    def CarbonConstraint(self, value):
        self._CarbonConstraint = value

    @property
    def Carbon(self) -> DataContainer:
        return self._Carbon

    @Carbon.setter
    def Carbon(self, value):
        self._Carbon = value

    @property
    def CarbonShadowPrice(self) -> DataContainer:
        return self._CarbonShadowPrice

    @CarbonShadowPrice.setter
    def CarbonShadowPrice(self, value):
        self._CarbonShadowPrice = value


class WorldPriceData(DataContainer):

    def __init__(self, filepath):
        super().__init__(filepath)
        self._ExogenWorldPrice = DataContainer(filepath)

    @property
    def ExogenWorldPrice(self) -> DataContainer:
        return self._ExogenWorldPrice

    @ExogenWorldPrice.setter
    def WorldPrice(self, value):
        self._Commodity = value

class __WorldDataCollector__(dict):
    """
    Temporary Structure in case of Bugs...
    """

    def __init__(self, filepath):
        super().__init__({
            "filepath": filepath,
            "data": pd.DataFrame(),
            "domain": None,
            "_temporary_attr_storage": [],
            "Demand": DataContainer(filepath),
            "Regions": DataContainer(filepath),
            "Commodities": DataContainer(filepath),
            "Specification": DataContainer(filepath),
            "Supply": DataContainer(filepath),
            "RecyclingS": DataContainer(filepath),
            "Forest": DataContainer(filepath),
            "Manufacture": DataContainer(filepath),
            "ManufactureCost": DataContainer(filepath),
            "ManufactureCoefficients": DataContainer(filepath),
            "Transportation": DataContainer(filepath),
            "TransportationImport": DataContainer(filepath),
            "TransportationExport": DataContainer(filepath),
            "ExogChange": DataContainer(filepath),
            "ExogChangeSupply": DataContainer(filepath),
            "ExogChangeDemand": DataContainer(filepath),
            "ExogChangeForest": DataContainer(filepath),
            "ExogChangeTrade": DataContainer(filepath),
            "ExogChangeTradeImport": DataContainer(filepath),
            "ExogChangeTradeExport": DataContainer(filepath),
            "ExogChangeManufactureCost": DataContainer(filepath),
            "ExogChangeManufactureCoefficients": DataContainer(filepath)
        })

    def set_attribute(self, name: str, value) -> None:
        """
        Method to set attributes from outside class to instance of object.
        :param name: Sets name of added attribute
        :param value: Sets value of added attribute
        """
        if name not in self.__dict__.keys():
            self.__setitem__(name, value)

    def __repr__(self) -> repr:
        """
        Override representation of object.
        :return: repr
        """
        return repr(f"Content from {os.path.basename(self.filepath)}; Sheet: {self.domain}")

    def __getattr__(self, item):
        return self.__getitem__(item)

    def add_temporary_attr(self, attribute_name):
        self._temporary_attr_storage.append(attribute_name)

    def clear_container(self):
        self._temporary_attr_storage.clear()

    def check_attr(self, attribute_name, temporary: bool = False):
        if (temporary is True) and (attribute_name not in self.__dict__.keys()):
            self.add_temporary_attr(attribute_name)
