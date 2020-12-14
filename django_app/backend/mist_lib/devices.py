
import requests
import json
import re
from .common import Common
from .ex_models import ex_ref


class Devices(Common):

    #############
    # get list of switches on a site
    #############
    def get_devices(self, body):
        body = self.get_body(body)
        if "site_id" in body:
            return self._get_devices(body)
        else:
            return {"status": 500, "data": {"message": "site_id missing"}}

    def _get_devices(self, body):
        site_id = body["site_id"]
        try:
            extract = self.extractAuth(body)
            limit = 1000
            page = 1
            results = []
            total = 1
            while len(results) < int(total) and int(page) < 50:
                device_type = "switch"
                url = "https://{0}/api/v1/sites/{1}/devices?type={2}&limit={3}&page={4}".format(
                    extract["host"], site_id, device_type, limit, page)
                resp = requests.get(
                    url, headers=extract["headers"], cookies=extract["cookies"])
                results.extend(resp.json())
                total = resp.headers["X-Page-Total"]
                page += 1
            return self._get_devices_vc(extract, site_id, results)

        except:
            return {"status": 500, "data": {"message": "Unable to retrieve the inventory"}}

    def _get_devices_vc(self, extract, site_id, devices):
        data = []
        for device in devices:
            try:
                device_id = "00000000-0000-0000-1000-{0}".format(device["mac"])
                url = "https://{0}/api/v1/sites/{1}/devices/{2}/vc".format(
                    extract["host"], site_id, device_id)
                resp = requests.get(
                    url, headers=extract["headers"], cookies=extract["cookies"])
                data.append(resp.json())
            except:
                return {"status": 500, "data": {"message": "Unable to retrieve information for device {0}".format(device_id)}}
        return {"status": 200, "data": {"total": len(data), "results": data}}


#############
# Get Device Settings
#############
# body: site_id, device_id, device_name, device_role, device_model

    def get_device_settings(self, body):
        body = self.get_body(body)
        if not "site_id" in body:
            return {"status": 500, "data": {"message": "site_id missing"}}
        if not "device_id" in body:
            return {"status": 500, "data": {"message": "device_id missing"}}
        else:
            extract = self.extractAuth(body)
            device_settings = self._get_device_settings(extract, body)
            device_stats = self._get_device_stats(extract, body)
            site_settings = self._get_site_template(extract, body)
            networks = self._generate_networks(site_settings, device_settings)
            if not "status" in device_settings and not "status" in site_settings:
                data = self._generate_device_settings(
                    device_settings, site_settings, device_stats)
                return {"status": 200, "data": {"members": data["members"], "networks": networks, "ports": data["ports"], "site": site_settings, "device": device_settings}}


    def _generate_networks(self, site_config, device_config):
        networks = site_config["networks"] if "networks" in site_config else {}
        device_networks = device_config["networks"] if "networks" in device_config else {}
        for network in device_networks:
            networks[network] = device_networks[network]
        return networks

    def _get_device_settings(self, extract, body):
        device_config = {
            "networks": {},
            "port_usages": {},
            "port_config": {}
        }
        try:
            url = "https://{0}/api/v1/sites/{1}/devices/{2}".format(
                body["host"], body["site_id"], body["device_id"])
            resp = requests.get(
                url, headers=extract["headers"], cookies=extract["cookies"])
            device_setting = resp.json()
            device_config["networks"] = device_setting["networks"] if "networks" in device_setting else {}
            device_config["port_usages"] = device_setting["port_usages"] if "port_usages" in device_setting else {}
            device_config["port_config"] = device_setting["port_config"] if "port_config" in device_setting else {}
            return device_config
        except:
            return {"status": 500, "data": {"message": "Unable to retrieve the device settings"}}

    def _get_device_stats(self, extract, body):
        try:
            url = "https://{0}/api/v1/sites/{1}/stats/devices/{2}".format(
                extract["host"], body["site_id"], body["device_id"])
            resp = requests.get(
                url, headers=extract["headers"], cookies=extract["cookies"])
            return resp.json()
        except:
            return {"status": 500, "data": {"message": "Unable to retrieve information for device {0}".format(body["device_id"])}}

    def _get_site_template(self, extract, body):
        try:
            url = "https://{0}/api/v1/sites/{1}/setting/derived".format(
                body["host"], body["site_id"])
            resp = requests.get(
                url, headers=extract["headers"], cookies=extract["cookies"])
            site_setting = resp.json()
            return self._parse_site_template(body, site_setting)
        except:
            return {"status": 500, "data": {"message": "Unable to retrieve the site settings"}}

    def _parse_site_template(self, body, site_setting):
        if "switch_matching" in site_setting:
            device_name = body["device_name"] if "device_name" in body else ""
            device_role = body["device_role"] if "device_role" in body else ""
            device_model = body["device_model"] if "device_model" in body else ""
            site_port_config = {}
            site_networks = {}
            site_port_usages = {}
            if "enable" in site_setting["switch_matching"] and site_setting["switch_matching"]["enable"]:
                rules = site_setting["switch_matching"]["rules"] if "rules" in site_setting["switch_matching"] else {
                }
                site_networks = site_setting["networks"] if "networks" in site_setting else {
                }
                site_port_usages = site_setting["port_usages"] if "port_usages" in site_setting else {
                }

                for rule in rules:
                    match = True
                    for key in rule:
                        if key == "match_model":
                            if not device_model.startswith(rule[key]):
                                match = False
                        if key == "role_name":
                            if not device_role == rule[key]:
                                match = False
                        if key.startswith("match_name"):
                            sub = rule[key].replace(
                                "match_name[", "").replace("]", "").split(":")
                            start = sub[0]
                            end = sub[1]
                            if not device_name[start:end] == rule[key]:
                                match = False
                    if match and "port_config" in rule:
                        site_port_config = rule["port_config"]
                        break
            return {"port_config": site_port_config, "networks": site_networks, "port_usages": site_port_usages}
        else:
            return {"networks": {}, "port_usages": {}, "port_config": {}}

    def _generate_device_settings(self, device_settings, site_settings, device_stats):
        data = {
            "members": [],
            "ports": {}
        }
        fpc = 0
        # Add information about each member of the VC (or the standalone)
        for member in device_stats["module_stat"]:
            tmp = {
                "mac": member["mac"] if "mac" in member else "None",
                "model": member["model"] if "model" in member else "None",
                "serial": member["serial"] if "serial" in member else "None",
                "vc_state": member["vc_state"] if "vc_state" in member else "None",
                "poe": member["poe"] if "poe" in member else "None",
                "fans": member["fans"] if "fans" in member else "None",
                "uptime": member["uptime"] if "uptime" in member else "None",
                "temperatures": member["temperatures"] if "temperatures" in member else "None",
                "vc_links": member["vc_links"] if "vc_links" in member else "None",
                "psus": member["psus"] if "psus" in member else "None",
                "vc_role": member["vs_role"] if "vs_role" in member else "None",
                "ports": [],
                "columns": {
                    "rj45": 0,
                    "sfp": 0
                }
            }

            # Generate the list of ports based on the HW model
            dev = ex_ref[member["model"]]
            for i in range(0, dev["rj45"]):
                tmp["ports"].append("ge-{0}/0/{1}".format(fpc, i))
                data["ports"]["ge-{0}/0/{1}".format(fpc, i)] = {
                    "port": "ge-{0}/0/{1}".format(fpc, i), "site": {}, "device": {}}
            for i in range(0, dev["sfp"]):
                tmp["ports"].append("xe-{0}/1/{1}".format(fpc, i))
                data["ports"]["xe-{0}/1/{1}".format(fpc, i)] = {
                    "port": "xe-{0}/1/{1}".format(fpc, i), "site": {}, "device": {}}
            data["members"].append(tmp)
            fpc += 1

        data = self._translate_mist_conf(data, site_settings, "site")
        data = self._translate_mist_conf(data, device_settings, "device")

        return data

    def _translate_mist_conf(self, data, config, scope):
        if "port_config" in config and config["port_config"]:
            # for each port config (means ge-0/0/0) or ports range config (means ge-0-2/0-1/0-10)
            for port_config in config["port_config"]:
                # if port config (means ge-0/0/0)
                if re.match(r'^[a-z]+-[0-9]+/[0-9]+/[0-9]+$', port_config):
                    fpc = int(port_config.split("-", 1)[1].split("/")[0])
                    if port_config in data["ports"]:
                        data["ports"][port_config][scope] = config["port_config"][port_config]
                    else:
                        data["ports"][port_config] = {
                            "port": port_config, "site": {}, "device": {}}
                        data["ports"][port_config][scope] = config["port_config"][port_config]

                # else, it's a ports range config (means ge-0-1/0-2/0-10)
                else:
                    port_config_split = port_config.split(",")
                    for port_config_item in port_config_split:
                        port_type = port_config_item.split("-", 1)[0]
                        fpc = port_config_item.split("-", 1)[1].split("/")[0].split("-")
                        pic = port_config_item.split("-", 1)[1].split("/")[1].split("-")
                        slot = port_config_item.split(
                            "-", 1)[1].split("/")[2].split("-")
                        for i in range(int(fpc[0]), int(fpc[-1])+1):
                            for j in range(int(pic[0]), int(pic[-1])+1):
                                for k in range(int(slot[0]), int(slot[-1])+1):
                                    interface = "{0}-{1}/{2}/{3}".format(
                                        port_type, i, j, k)
                                    if interface in data["ports"]:
                                        data["ports"][interface][scope] = config["port_config"][port_config]
                                    else:
                                        data["ports"][interface] = {
                                            "port": interface, "site": {}, "device": {}}
                                        data["ports"][interface][scope] = config["port_config"][port_config]
        return data

    #############
    # Update Device Settings
    #############

    def update_device_settings(self, body):
        body = self.get_body(body)
        if "site_id" in body:
            return self._update_device_settings(body)
        else:
            return {"status": 500, "data": {"message": "site_id missing"}}

    def _update_device_settings(self, body):
        extract = self.extractAuth(body)
        if "device_id" in body:
            if "device_settings" in body:
                try:
                    url = "https://{0}/api/v1/sites/{1}/devices/{2}".format(
                        body["host"], body["site_id"], body["device_id"])
                    resp = requests.put(
                        url, headers=extract["headers"], cookies=extract["cookies"], json=body["device_settings"])
                    return {"status": 200, "data": {"result": resp.json()}}
                except:
                    return {"status": 500, "data": {"message": "unable to update the device"}}
            else:
                return {"status": 500, "data": {"message": "device_settings missing"}}
        else:
            return {"status": 500, "data": {"message": "device_id missing"}}


#############
# Get Device Ports Status
#############

    def get_device_ports_status(self, body):
        body = self.get_body(body)
        if "site_id" in body:
            return self._get_device_ports_status(body)
        else:
            return {"status": 500, "data": {"message": "site_id missing"}}

    def _get_device_ports_status(self, body):
        extract = self.extractAuth(body)
        if "mac" in body:
            try:
                url = "https://{0}/api/v1/sites/{1}/stats/switch_ports/search?mac={2}".format(
                    body["host"], body["site_id"], body["mac"])
                resp = requests.put(
                    url, headers=extract["headers"], cookies=extract["cookies"], json=body["device_settings"])
                return {"status": 200, "data": {"result": resp.json()}}
            except:
                return {"status": 500, "data": {"message": "unable to retrieve the device ports status"}}
        else:
            return {"status": 500, "data": {"message": "mac missing"}}


# Site level
# https://api.mist.com/api/v1/sites/f5fcbee5-fbca-45b3-8bf1-1619ede87879/setting/derived
# Switch level conf
# https://api.mist.com/api/v1/sites/f5fcbee5-fbca-45b3-8bf1-1619ede87879/devices/00000000-0000-0000-1000-2c21311c37b0
# Port status
# https://api.mist.com/api/v1/sites/f5fcbee5-fbca-45b3-8bf1-1619ede87879/wired_clients/search?device_mac=2c21311c37b0&start=1607356196
# Port stats
# https://api.mist.com/api/v1/sites/f5fcbee5-fbca-45b3-8bf1-1619ede87879/stats/switch_ports/search?mac=2c21311c37b0
# {
#     "switch_matching": {
#         "enable": true,
#         "rules": [
#             {
#                 "name": "ex-2300",
#                 "port_config": {
#                     "ge-0/0/10": {
#                         "usage": "lab_sta"
#                     },
#                     "ge-0/0/11": {
#                         "usage": "lab_wan"
#                     },
#                     "xe-0/1/0": {
#                         "usage": "lab_tun"
#                     },
#                     "ge-0/0/0-9": {
#                         "usage": "lab_reg",
#                         "dynamic_usage": "dynamic"
#                     }
#                 },
#                 "additional_config_cmds": [
#                     ""
#                 ],
#                 "match_model[0:6]": "EX2300"
#             }
#         ]
#     },
#     "networks": {
#         "iot": {
#             "vlan_id": "8"
#         }
#     },
#     "port_usages": {
#         "lab_iot": {
#             "name": "lab_iot",
#             "mode": "access",
#             "disabled": false,
#             "port_network": "iot",
#             "stp_edge": true,
#             "all_networks": false,
#             "networks": [],
#             "port_auth": "dot1x",
#             "enable_mac_auth": true,
#             "guest_network": null,
#             "bypass_auth_when_server_down": false
#         },
#         "lab_tun": {
#             "name": "lab_tun",
#             "mode": "trunk",
#             "disabled": false,
#             "port_network": "tun",
#             "stp_edge": false,
#             "all_networks": true,
#             "networks": [],
#             "port_auth": null,
#             "speed": "auto",
#             "duplex": "auto",
#             "mac_limit": 0,
#             "poe_disabled": true
#         },
#         "dynamic": {
#             "mode": "dynamic",
#             "rules": [
#                 {
#                     "src": "radius_dynamicfilter",
#                     "usage": "lab_ap",
#                     "equals": "wireless",
#                     "expression": "[0:8]"
#                 },
#                 {
#                     "src": "radius_dynamicfilter",
#                     "usage": "lab_ap_test",
#                     "equals": "aerohive",
#                     "expression": "[0:8]"
#                 },
#                 {
#                     "src": "link_peermac",
#                     "usage": "lab_wan",
#                     "equals": "90:a2:da",
#                     "expression": "[0:8]"
#                 }
#             ]
#         }
#     },
#     "dynamic": {
#         "mode": "dynamic",
#         "rules": [
#             {
#                 "src": "radius_dynamicfilter",
#                 "usage": "lab_ap",
#                 "equals": "wireless"
#             },
#             {
#                 "src": "radius_dynamicfilter",
#                 "usage": "lab_ap_test",
#                 "equals": "aerohive"
#             }
#         ]
#     },