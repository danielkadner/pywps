"""
This module parses OGC Web Processing Service (WPS) Execute request.
"""
# Author:	Jachym Cepicky
#        	http://les-ejk.cz
#               jachym at les-ejk dot cz
# Lince: 
# 
# Web Processing Service implementation
# Copyright (C) 2006 Jachym Cepicky
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import xml.dom.minidom
from pywps.Parser.Post import Post

import string,re

class Post(Post):
    """ HTTP POST XML request encoding parser.  """

    wps = None # main WPS instance
    document = None # input DOM object
    inputs = {} # resulting parsed inputs
    nameSpace = None # WPS namespace
    owsNameSpace = None # OWS namespace
    xlinkNameSpace = None # OWS namespace

    def __init__(self,wps):
        """ Constructor """
        self.wps = wps

    def parse(self,document):
        """ Parse given XML document """
        self.document = document  # input DOM

        firstChild = self.getFirstChildNode(self.document)  # no comments or
                                                            # white spaces
        self.nameSpace = firstChild.namespaceURI    # document namespace
        self.owsNameSpace = self.wps.OWS_NAMESPACE  
        self.xlinkNameSpace = self.wps.XLINK_NAMESPACE
        language  = None
        identifiers = []
        identifierNode = None
        dataInputs = None

        #
        # Mandatory options
        #
        
        # service
        self.wps.inputs["service"] = "wps"
        
        # request 
        self.wps.inputs["request"] = "execute"

        # version
        self.wps.inputs["version"] = firstChild.getAttribute("version")
        if not self.wps.inputs["version"]:
            raise self.wps.exceptions.MissingParameterValue("version")

        # identifier
        try:
            self.wps.inputs["identifier"] =\
            firstChild.getElementsByTagNameNS(self.owsNameSpace,"Identifier")[0].firstChild.nodeValue
        except IndexError:
                raise self.wps.exceptions.MissingParameterValue("Identifier")

        #
        # Optional options
        #
            
        # language
        language = firstChild.getAttribute("language")
        if not language:
            language = self.wps.defaultLanguage

        self.wps.inputs["language"] = language

        # dataInputs
        try:
            inputsNode = firstChild.getElementsByTagNameNS(
                                            self.nameSpace,"DataInputs")[0]
            self.wps.inputs["datainputs"] = self.parseDataInputs(inputsNode) 
        except IndexError:
            self.wps.inputs["datainputs"] = None

        # responseForm
        try:
            responseFormNode = \
                firstChild.getElementsByTagNameNS(self.nameSpace,
                                                        "ResponseForm")[0]
            self.wps.inputs["responseform"] = self.parseResponseForm(
                                                        responseFormNode) 
        except IndexError:
            self.wps.inputs["responseform"] = None


    def parseResponseForm(self,responseFormNode):
        """ Parse requested response form node """
        
        form = {}
        form["responsedocument"] = {}
        form["rawdataoutput"] = {}

        # ResponseDocument
        try:
            responseDocumentNode = responseFormNode.getElementsByTagNameNS(
                                    self.nameSpace, "ResponseDocument")[0]
            form["responsedocument"] = {}

            # store
            store = False
            if responseDocumentNode.getAttributeNS(self.nameSpace,
                    "storeExecuteResponse").lower() == "true":
                form["responsedocument"]["storeexecuteresponse"]=True
            else:
                form["responsedocument"]["storeexecuteresponse"]=False

            # lineage
            lineage = False
            if responseDocumentNode.getAttributeNS(self.nameSpace,
                    "lineage").lower() == "true":
                form["responsedocument"]["lineage"]=True
            else:
                form["responsedocument"]["lineage"]=False

            # status
            status = False
            if responseDocumentNode.getAttributeNS(self.nameSpace,
                    "status").lower() == "true":
                form["responsedocument"]["status"]=True
            else: 
                form["responsedocument"]["status"]=False

            form["responsedocument"]["outputs"] = {}
            outputs = []
            for outputNode in responseDocumentNode.getElementsByTagNameNS(
                                                self.nameSpace, "Output"):

                try:
                    # identifier
                    identifier = outputNode.getElementsByTagNameNS(
                                    self.owsNameSpace,
                                    "Identifier")[0].firstChild.nodeValue
                    outputs.append({"identifier": identifier})
                except IndexError:
                    raise self.wps.exceptions.MissingParameterValue("Identifier")
                # Abstract, Title are not supported yet
                # is it necessary ?

                outputs[-1]["mimetype"] = \
                    outputNode.getAttributeNS("*","mimeType") 
                outputs[-1]["encoding"] = \
                    outputNode.getAttributeNS("*","encoding") 
                outputs[-1]["schema"] = \
                    outputNode.getAttributeNS("*","schema") 
                outputs[-1]["uom"] = \
                    outputNode.getAttributeNS(self.nameSpace,"uom") 

                outputs[-1]["asreference"] = False
                if outputNode.getAttributeNS(
                        self.nameSpace,"asReference").lower() == "true":
                    outputs[-1]["asreference"] = True

            form["responsedocument"]["outputs"] = outputs

        # RawDataOutput
        except IndexError:
            responseFormNode.getElementsByTagNameNS(self.nameSpace,
                                                    "RawDataOutput")
            form["rawdataoutput"] = {}
            try:
                # identifier
                identifier = responseFormNode.getElementsByTagNameNS(
                                self.owsNameSpace,
                                "Identifier")[0].firstChild.nodeValue
                form["rawdataoutput"][identifier] = {}
            except IndexError:
                raise self.wps.exceptions.MissingParameterValue("Identifier")
            form["rawdataoutput"][identifier]["mimetype"] = \
                    responseFormNode.getAttributeNS("*","mimeType")
            form["rawdataoutput"][identifier]["encoding"] = \
                    responseFormNode.getAttributeNS("*","encoding")
            form["rawdataoutput"][identifier]["schema"] = \
                    responseFormNode.getAttributeNS("*","schema")
            form["rawdataoutput"][identifier]["uom"] = \
                    responseFormNode.getAttributeNS("*","uom")
        return form

    def parseDataInputs(self,inputsNode):
        """ Parse intput data from given node """

        parsedDataInputs = []
        
        for inputNode in inputsNode.getElementsByTagNameNS(self.nameSpace,
                                                                "Input"):
            # input Identifier
            try:
                identifier = inputNode.getElementsByTagNameNS(
                     self.owsNameSpace,"Identifier")[0].firstChild.nodeValue
            except IndexError:
                raise self.wps.exceptions.NoApplicableCode(
                                              "Identifer for input not set")

            parsedDataInputs.append({"identifier":identifier,"value":None,
                "attributes":{}})

            # Title and Abstract are only mandatory and not necessary:
            # skipping, not supported yet
            
            # formchoice
            try:
                dataTypeNode = inputNode.getElementsByTagNameNS(
                                            self.nameSpace,"Reference")[0]
                attributes = self.parseReferenceDataInput(dataTypeNode) 
                attributes["identifier"] = identifier
                parsedDataInputs[-1] = attributes
            except IndexError:
                dataTypeNode = inputNode.getElementsByTagNameNS(
                                                self.nameSpace,"Data")[0]
                attributes =self.parseDataInput(dataTypeNode) 
                attributes["identifier"] = identifier
                parsedDataInputs[-1] = attributes
            try:
                parsedDataInputs[-1]
            except KeyError:
                raise self.wps.exceptions.InvalidParameterValue(identifier)

                
        return parsedDataInputs

    def parseReferenceDataInput(self,dataTypeNode):
        """ Parse given complex value reference node """
        
        attributes = {}

        #
        # mandatrory attributes
        #
        attributes["value"] =\
                    dataTypeNode.getAttributeNS(self.xlinkNameSpace,"href")
        if attributes == "":
            raise self.wps.exceptions.MissingParameterValue("'href'")

        #
        # optional attributes
        #

        # mimeType, encoding, schema - not yet supported
        
        # method
        attributes["method"] = \
                   dataTypeNode.getAttributeNS(self.nameSpace,"method")
        if attributes["method"] == "":
            attributes["method"] = "GET"
        
        # header
        try:
            attributes["header"] = self.parseHeaderDataInput(
                                        dataTypeNode.getElementsByTagNameNS(
                                            self.nameSpace, "Header")[0])
        except IndexError:
            attributes["header"] = None

        # body
        try:
            attributes["body"] = \
                        dataTypeNode.getElementsByTagNameNS(self.nameSpace,
                        "Body")[0].firstChild
        
            # get node value, if node type is Text or CDATA
            if attributes["body"].nodeType == \
                                    xml.dom.minidom.Text.nodeType or\
            attributes["body"].nodeType ==\
                                    xml.dom.minidom.CDATASection.nodeType:
                attributes["body"] = attributes["body"].nodeValue
        except IndexError:
            attributes["body"] = None

        # bodyreference
        try:
            bodyReferenceNode = dataTypeNode.getElementsByTagNameNS(
                                        self.nameSpace,"BodyReference")[0]
            attributes["bodyreference"] = bodyReferenceNode.getAttributeNS(
                                                self.xlinkNameSpace,"href")
        except IndexError:
            attributes["bodyreference"] = None

        attributes["type"] = "ComplexValue"
        attributes["asReference"] = True
        
        return attributes

    def parseHeaderDataInput(self,headerNode):
        """ Parse hearder node """

        header = {}

        if headerNode:
            header[headerNode.getAttributeNS(self.nameSpace,"key")] =\
                        headerNode.getAttributeNS(self.nameSpace,"value")

            if len(header.keys()) == 0:
                raise self.wps.exeptions.MissingParameterValue("Header")

        return header

    def parseDataInput(self,dataTypeNode):
        """Parse attributes of given data type node """

        attributes = None

        # complexData
        if len(dataTypeNode.getElementsByTagNameNS(
                                    self.nameSpace,"ComplexData")) > 0:
            attributes = self.parseComplexData(
                                dataTypeNode.getElementsByTagNameNS(
                                           self.nameSpace,"ComplexData")[0])
            
        # literalData
        elif len(dataTypeNode.getElementsByTagNameNS(
                                    self.nameSpace,"LiteralData")) > 0:
            attributes = self.parseLiteralData(
                                dataTypeNode.getElementsByTagNameNS(
                                           self.nameSpace,"LiteralData")[0])
        # bboxData
        elif len(dataTypeNode.getElementsByTagNameNS(
                                    self.nameSpace,"BoundingBoxData")) > 0:
            attributes = self.parseBBoxData(
                                dataTypeNode.getElementsByTagNameNS(
                                       self.nameSpace,"BoundingBoxData")[0])

        # if attributes are still None, exception will 
        # be called in parent method

        return attributes

    def parseComplexData(self,complexDataNode):
        """Parse complex data node"""

        attributes = {}
        attributes["mimetype"] = complexDataNode.getAttributeNS(
                                        "*","mimeType")
        attributes["encoding"] = complexDataNode.getAttributeNS(
                                        "*","encoding")
        attributes["schema"] = complexDataNode.getAttributeNS(
                                        "*","schema")
        for complexDataChildNode in complexDataNode.childNodes:
            if complexDataChildNode.nodeType == \
                xml.dom.minidom.Text.nodeType or \
                complexDataChildNode.nodeType == \
                xml.dom.minidom.CDATASection.nodeType:
                attributes["value"] = complexDataChildNode.nodeValue
            elif complexDataChildNode.nodeType == \
                    xml.dom.minidom.Element.nodeType:
                attributes["value"] = complexDataChildNode.toxml()

        attributes["type"] = "ComplexValue"
            
        return attributes
    
    def parseLiteralData(self,literalDataNode):
        """Parse literal data node"""

        attributes = {}
        attributes["dataType"] = literalDataNode.getAttributeNS(
                                        "*","dataType")
        attributes["uom"] = literalDataNode.getAttributeNS(
                                        "*","uom")
        attributes["value"] = literalDataNode.firstChild.nodeValue
        return attributes

    def parseBBoxData(self,bboxDataNode):
        """Parse bbox data node"""

        attributes = {}
        attributes["value"] = []
        attributes["crs"] = bboxDataNode.getAttributeNS(self.owsNameSpace,
                                                                    "crs")
        attributes["dimensions"] = int(bboxDataNode.getAttributeNS(
                                        self.owsNameSpace, "dimensions"))

        for coord in bboxDataNode.getElementsByTagNameNS(
                self.owsNameSpace,"LowerCorner")[0].nodeValue.split():
            attributes["value"].append(coord)
        for coord in bboxDataNode.getElementsByTagNameNS(
                self.owsNameSpace,"UpperCorner")[0].nodeValue.split():
            attributes["value"].append(coord)

        # reset everything, if there are not 4 coordinates
        if len(attributes["value"]) != 4:
            attributes = None
        return attributes


class Get:
    """
    Parses input request obtained via HTTP GET encoding.
    """

    wps = None  # main WPS instance
    unparsedInputs = {} # input arguments
    inputs = {} # resulting parsed inputs

    def __init__(self,wps):
        """
        Arguments:
           self
           wps   - parent WPS instance
        """
        self.wps = wps

    def parse(self,unparsedInputs):
        """ Parse given inputs """

        self.unparsedInputs = unparsedInputs

        #
        # Mandatory options
        #

        # service (is allready controled)
        if self.unparsedInputs["service"].lower() == "wps":
            self.wps.inputs["service"] = self.unparsedInputs["service"].lower()

        # Request (is allready controled)
        if self.unparsedInputs["request"].lower() == "execute":
            self.wps.inputs["request"] = self.unparsedInputs["request"].lower()

        # version
        self.wps.inputs["version"] = self.unparsedInputs["version"]

        # identifier
        self.wps.inputs["identifier"] = self.unparsedInputs["identifier"]

        # 
        # Optional options
        #

        # Language
        try:
            self.wps.inputs["language"] =\
                                    self.unparsedInputs["language"].lower()
        except KeyError,e:
            self.wps.inputs["language"] = self.wps.defaultLanguage

        # dataInputs
        try:
            self.wps.inputs["datainputs"] = self.parseDataInputs(
                        self.unparsedInputs["datainputs"])
        except KeyError:
            self.wps.inputs["datainputs"] = {}

        # ResponseForm

        self.wps.inputs["responseform"] = {}

        # ResponseDocument
        try:
            self.wps.inputs["responseform"]["responsedocument"] = \
                    {"outputs":  self.parseDataInputs(
                                self.unparsedInputs["responsedocument"])}
        except KeyError:
            self.wps.inputs["responseform"]["responsedocument"] = {}

        # RawDataOutput
        try:
            self.wps.inputs["responseform"]["rawdataoutput"] = \
                                    self.parseDataInputs(
                                    self.unparsedInputs["rawdataoutput"])
        except KeyError:
            self.wps.inputs["responseform"]["rawdataoutput"] = {}

        # storeExecuteResponse
        try:
            if self.unparsedInputs["storeexecuteresponse"].lower() ==\
                                                                    "true":
                self.wps.inputs["responseform"]["responsedocument"]["storeexecuteresponse"] = True
            else:
                self.wps.inputs["responseform"]["responsedocument"]["storeexecuteresponse"] = False

        except KeyError:
            self.wps.inputs["responseform"]["responsedocument"]["storeexecuteresponse"] = False

        # lineage
        try:
            if self.unparsedInputs["lineage"].lower() == "true":
                self.wps.inputs["responseform"]["responsedocument"]["lineage"]=\
                                                                        True
            else:
                self.wps.inputs["responseform"]["responsedocument"]["lineage"]=\
                                                                       False

        except KeyError:
            self.wps.inputs["responseform"]["responsedocument"]["lineage"]=\
                                                                      False
        # status
        try:
            if self.unparsedInputs["status"].lower() == "true":
                self.wps.inputs["responseform"]["responsedocument"]["status"]=\
                                                                        True
            else:
                self.wps.inputs["responseform"]["responsedocument"]["status"]=\
                                                                      False

        except KeyError:
            self.wps.inputs["responseform"]["responsedocument"]["status"] =\
                                                                      False


    def parseDataInputs(self,dataInputs):
        """Parse DataInputs parameter

        This is described in OGC WPS 1.0.0,  05-007, page 38 
        
        """

        parsedDataInputs = []

        # Parameters are separated by ";"
        for dataInput in dataInputs.split(";"):
            try:
                # key is separated by "=" from value
                key,value = string.split(dataInput,"=",maxsplit=1)
            except ValueError,e:
                key = dataInput
                value = ""

            if not key and not value:
                continue

            # initial value
            parsedDataInputs.append({"identifier":key, "value":None})
            
            # aditional input attributes are separated by "@"
            attributes = []
            if value.find("@") > 0:
                parsedDataInputs[-1]["value"]=value.split("@")[0]
                attributes=value.split("@")[1:]
            elif value.find("@") == 0:
                parsedDataInputs[-1]["value"]=None
                attributes=value.split("@")[1:]
            else:
                parsedDataInputs[-1]["value"]=value
                attributes = []

            # aditional attribute key is separated by "=" from it's value
            for attribute in attributes:
                attributeKey, attributeValue = attribute.split("=")
                parsedDataInputs[-1][attributeKey.lower()] =\
                                                    self._trueOrFalse(attributeValue)
        return parsedDataInputs

    def _trueOrFalse(self,str):
        """Return True or False, if input is "true" or "false" """

        if str.lower() == "false":
            return False
        elif str.lower() == "true":
            return True
        else:
            return str
