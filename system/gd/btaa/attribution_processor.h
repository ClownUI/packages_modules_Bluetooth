/*
 * Copyright 2020 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#pragma once

#include <cstdint>
#include <unordered_map>

#include "hci_processor.h"

namespace bluetooth {
namespace activity_attribution {

static constexpr size_t kWakeupAggregatorSize = 200;

struct AddressActivityKey {
  hci::Address address;
  Activity activity;

  bool operator==(const AddressActivityKey& other) const {
    return (address == other.address && activity == other.activity);
  }
};

struct AddressActivityKeyHasher {
  std::size_t operator()(const AddressActivityKey& key) const {
    return (
        (std::hash<std::string>()(key.address.ToString()) ^
         (std::hash<unsigned char>()(static_cast<unsigned char>(key.activity)))));
  }
};

struct AppActivityKey {
  std::string app;
  Activity activity;

  bool operator==(const AppActivityKey& other) const {
    return (app == other.app && activity == other.activity);
  }
};

struct AppActivityKeyHasher {
  std::size_t operator()(const AppActivityKey& key) const {
    return (
        (std::hash<std::string>()(key.app) ^ (std::hash<unsigned char>()(static_cast<unsigned char>(key.activity)))));
  }
};

struct DeviceWakeupDescriptor {
  Activity activity_;
  const hci::Address address_;
  DeviceWakeupDescriptor(Activity activity, const hci::Address address) : activity_(activity), address_(address) {}
  virtual ~DeviceWakeupDescriptor() {}
};

struct AppWakeupDescriptor {
  Activity activity_;
  std::string package_info_;
  AppWakeupDescriptor(Activity activity, std::string package_info) : activity_(activity), package_info_(package_info) {}
  virtual ~AppWakeupDescriptor() {}
};

class AttributionProcessor {
 public:
  void OnBtaaPackets(std::vector<BtaaHciPacket> btaa_packets);
  void OnWakelockReleased(uint32_t duration_ms);
  void OnWakeup();
  void NotifyActivityAttributionInfo(int uid, const std::string& package_name, const std::string& device_address);
  void Dump(
      std::promise<flatbuffers::Offset<ActivityAttributionData>> promise, flatbuffers::FlatBufferBuilder* fb_builder);

 private:
  bool wakeup_ = false;
  std::unordered_map<AddressActivityKey, BtaaAggregationEntry, AddressActivityKeyHasher> btaa_aggregator_;
  std::unordered_map<AddressActivityKey, BtaaAggregationEntry, AddressActivityKeyHasher> wakelock_duration_aggregator_;
  std::unordered_map<std::string, std::string> address_app_map_;
  std::unordered_map<AppActivityKey, BtaaAggregationEntry, AppActivityKeyHasher> app_activity_aggregator_;
  common::TimestampedCircularBuffer<DeviceWakeupDescriptor> device_wakeup_aggregator_ =
      common::TimestampedCircularBuffer<DeviceWakeupDescriptor>(kWakeupAggregatorSize);
  common::TimestampedCircularBuffer<AppWakeupDescriptor> app_wakeup_aggregator_ =
      common::TimestampedCircularBuffer<AppWakeupDescriptor>(kWakeupAggregatorSize);
  const char* ActivityToString(Activity activity);
};

}  // namespace activity_attribution
}  // namespace bluetooth
