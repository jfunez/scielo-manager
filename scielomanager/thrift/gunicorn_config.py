#coding: utf-8


worker_class = "thriftpy_gevent"
#worker_class = "thriftpy_sync"


thrift_protocol_factory = "thriftpy.protocol:TCyBinaryProtocolFactory"
thrift_transport_factory = "thriftpy.transport:TCyBufferedTransportFactory"

errorlog = "-"
loglevel = "info"

