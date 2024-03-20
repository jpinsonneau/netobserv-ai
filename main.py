import json
import os

import logging
import socket
from confluent_kafka import Producer, Consumer
from river import naive_bayes, compose, preprocessing

model = compose.Pipeline(
            preprocessing.FeatureHasher(),
            preprocessing.MinMaxScaler(),
            naive_bayes.GaussianNB()
        )

def formatRecord(record):
    # remove collector / Src / Dst related fields
    record.pop("AgentIP", None)

    record.pop("SrcAddr", None)
    record.pop("DstAddr", None)

    record.pop("SrcMac", None)
    record.pop("DstMac", None)

    record.pop("SrcPort", None)
    record.pop("DstPort", None)

    record.pop("SrcK8S_Name", None)
    record.pop("DstK8S_Name", None)

    record.pop("SrcK8S_Type", None)
    record.pop("DstK8S_Type", None)

    record.pop("SrcK8S_OwnerName", None)
    record.pop("DstK8S_OwnerName", None)

    record.pop("SrcK8S_OwnerType", None)
    record.pop("DstK8S_OwnerType", None)

    record.pop("SrcK8S_HostIP", None)
    record.pop("DstK8S_HostIP", None)

    record.pop("SrcK8S_HostName", None)
    record.pop("DstK8S_HostName", None)

    # remove time related fields
    record.pop("TimeFlowStartMs", None)
    record.pop("TimeFlowEndMs", None)
    record.pop("TimeReceived", None)

    # replace arrays to string since predict proba doesn't support these
    record["Interfaces"] = ','.join(str(i) for i in record["Interfaces"])
    record["IfDirections"] = ','.join(str(i) for i in record["IfDirections"])

    return record

def cleanupRecord(record, key):
    r = {}
    
    for attribute, value in record.items():
      if key in attribute:
        r[key] = attribute

    return r

def learnOne(record, label):
    try:
        model.learn_one(record, label)
        print(f"learned {label}\n")
    except Exception as e:
        logging.exception("Couldn't learn one record")
        print(f"Error: {e}\n")
    
    return

def leanFromFile(filename, title, label):
    print(f"Reading flows containing {title}...")
    f = open(filename)
    js = json.load(f)

    for stream in js["data"]["result"]:
        # print(stream)
        for v in stream["values"]:
            record = formatRecord(json.loads(v[1]))
            print(record)
            learnOne(record, label)

    return

def initialLearning():
    leanFromFile("recordsOK.json", "OK content", "ok")
    leanFromFile("recordsDropped.json", "drops", "drops")
    leanFromFile("recordsDNSError.json", "DNS errors", "dnserr")
    leanFromFile("recordsHighRTT.json", "high RTT", "highrtt")
    
    return

def create_consumer(server, topic, group_id):
    try:
        consumer = Consumer({"bootstrap.servers": server,
                             "group.id": group_id,
                             "client.id": socket.gethostname(),
                             "isolation.level": "read_committed",
                             "default.topic.config": {"auto.offset.reset": "latest", # Only consume new messages
                                                      "enable.auto.commit": True}
                             })

        consumer.subscribe([topic])
    except Exception as e:
        logging.exception("Couldn't create the consumer")
        consumer = None

    return consumer

def detect():
    consumer = create_consumer(server="kafka-cluster-kafka-bootstrap.netobserv",
                               topic="network-flows",
                               group_id="test")

    print("Predict flows category")
    while True:
        message = consumer.poll(timeout=50)
        if message is None:
            continue
        if message.error():
            logging.error("Consumer error: {}".format(message.error()))
            continue
        record = formatRecord(json.loads(message.value().decode('utf-8')))
        print(record)
        try:
            prediction = model.predict_proba_one(record)
            if prediction["drops"] > 0.75:
              print("--> ALERT -- DROP FOUND !")
              #learnOne(formatRecord(record), "drops")
            
            if prediction["dnserr"] > 0.75:
              print("--> ALERT -- DNS ERROR FOUND !")
              #learnOne(formatRecord(record), "dnserr")

            if prediction["highrtt"] > 0.75:
              print("--> ALERT -- HIGH RTT FOUND !")
              #learnOne(formatRecord(record), "highrtt")

            if prediction["ok"] > 0.75:
              print("--> OK")
              #learnOne(formatRecord(record), "ok")
            print(f'    Predict {prediction}\n')
        except Exception as e:
            print(f"Error: {e}\n")

    consumer.close()

initialLearning()
detect()