# Copyright 2020 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import asyncio

from avalon_sdk.connector.blockchains.ethereum.ethereum_listener \
    import BlockchainInterface, EventProcessor
from connector_common.base_connector import BaseConnector


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


class EthereumConnector(BaseConnector):
    """
    This class is the bridge between the Ethereum blockchain and the Avalon
    core. It listens for events generated by the Ethereum blockchain.
    It handles event data corresponding to the event (eg: workOrderSubmitted
    and submits requests to Avalon on behalf of the client. The service also
    invokes smart contract APIs (eg: workOrderComplete).
    """

    def __init__(self, config, eth_registry_instance, eth_worker_instance,
                 eth_work_order_instance, eth_wo_receipt_instance,
                 wo_contract_instance_evt):
        """
        initialize connector
        @param config - dict containing config params
        @param eth_registry_instance - object of EthereumWorkerRegistryListImpl
        @param eth_worker_instance - object of EthereumWorkerRegistryImpl
        @param eth_work_order_instance - object of EthereumWorkOrderProxyImpl
        @param eth_wo_receipt_instance - object of ethereum implementation for
        work order receipt
        @param wo_contract_instance_evt - wo event listener
        """
        super(EthereumConnector, self).__init__(
            config,
            eth_registry_instance,
            eth_worker_instance,
            eth_work_order_instance,
            eth_wo_receipt_instance
        )
        self._config = config
        self._wo_evt = wo_contract_instance_evt

    def start_wo_submitted_event_listener(self, handler_func):
        """
        Start event listener is blockchain specific
        and it is implemented using blockchain provided sdk
        @param handler_func is event handler function
        """
        # TODO: After creating APIs for event listening
        # This is also generalized
        # Start an event listener that listens for events from the proxy
        # blockchain, extracts request payload from there and make a request
        # to avalon-listener
        def workorder_event_handler_func(event, account, contract):
            """
            The function retrieves pertinent information
            from the event received and makes call to handler_func
            """
            try:
                work_order_request = json.loads(
                    event["args"]["workOrderRequest"])
            except Exception as err:
                logging.exception(
                    "Exception while parsing json {}".format(err))
            work_order_id = work_order_request["workOrderId"]
            worker_id = work_order_request["workerId"]
            requester_id = work_order_request["requesterId"]
            work_order_params = event["args"]["workOrderRequest"]
            handler_func(work_order_id, worker_id, requester_id,
                         work_order_params)

        w3 = BlockchainInterface(self._config)

        contract = self._wo_evt
        # Listening only for workOrderSubmitted event now
        listener = w3.newListener(contract, "workOrderSubmitted")

        try:
            daemon = EventProcessor(self._config)
            asyncio.get_event_loop().run_until_complete(daemon.start(
                listener,
                workorder_event_handler_func,
                account=None,
                contract=contract,
            ))
        except KeyboardInterrupt:
            asyncio.get_event_loop().run_until_complete(
                daemon.stop()
            )