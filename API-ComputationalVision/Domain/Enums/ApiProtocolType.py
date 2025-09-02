from enum import Enum


class ApiProtocolType(str, Enum):
    REST = "REST"
    SOAP = "SOAP"
    GRAPHQL = "GRAPHQL"
    WEBSOCKET = "WEBSOCKET"
    RPC = "RPC"
    gRPC = "gRPC"