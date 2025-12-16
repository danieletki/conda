=====================
BLE Penetration Guide
=====================

This guide provides comprehensive documentation for conducting Bluetooth Low Energy (BLE)
penetration testing using the conda BLE penetration tools. It covers prerequisites,
configuration, safety considerations, and detailed workflows for various attack scenarios.

Prerequisites
=============

System Requirements
-------------------

* **Operating System**: Linux, macOS, or Windows with Bluetooth hardware support
* **Python**: 3.8 or later
* **Bluetooth Hardware**: BLE-compatible adapter (built-in or USB dongle)

Required Libraries
------------------

The following libraries are essential for BLE penetration testing:

* **bleak** - Cross-platform BLE library for Python
* **Frida** - Dynamic instrumentation toolkit for security research
* **Platform-specific SDKs**:
  - On **Linux**: BlueZ (usually pre-installed)
  - On **macOS**: Native CoreBluetooth APIs (built-in)
  - On **Windows**: Windows 10+ with native BLE support or Zadig-configured USB drivers

Installation
^^^^^^^^^^^^

Install the BLE penetration testing dependencies:

.. code-block:: bash

    pip install -r tools/ble_pentest/requirements-ble.txt

Or as an optional dependency group in conda:

.. code-block:: bash

    pip install conda[ble-pentest]

Configuration Schema
====================

Attack Configuration
--------------------

The BLE penetration tools use YAML-based configuration files to define attack parameters.
Configuration files should follow this schema:

.. code-block:: yaml

    # Global settings
    global:
      # Enable verbose output (true/false)
      verbose: false
      # Timeout for device discovery in seconds
      discovery_timeout: 10
      # Maximum devices to track simultaneously
      max_devices: 100
      # Log file path (optional)
      log_file: null

    # Target device specifications
    target:
      # Device address (e.g., "AA:BB:CC:DD:EE:FF")
      address: null
      # Device name pattern (supports wildcards)
      name_pattern: null
      # Service UUID to target
      service_uuid: null
      # Characteristic UUIDs to interact with
      characteristics: []

    # Attack-specific parameters
    attack:
      # Type of attack: "scan", "pairing", "mitm", "fuzzing", "replay"
      type: "scan"
      # Attack timeout in seconds
      timeout: 30
      # Attempt reconnection (true/false)
      retry_on_failure: true
      # Retry attempts count
      max_retries: 3
      # Delay between retries in seconds
      retry_delay: 2

    # Report generation settings
    reporting:
      # Output format: "json", "html", "pdf"
      format: "json"
      # Include detailed packet captures
      include_captures: false
      # Output file path
      output_file: "ble_report.json"
      # Include recommendations
      include_recommendations: true

    # Scope and authorization
    scope:
      # Authorized device addresses (CIDR notation supported)
      authorized_addresses: []
      # Authorized device names
      authorized_names: []
      # Authorized MAC address ranges
      authorized_ranges: []

Configuration Example
^^^^^^^^^^^^^^^^^^^^^

See ``tools/ble_pentest/examples/config_example.yaml`` for an annotated example configuration.

Safety Considerations
====================

Legal and Ethical Requirements
------------------------------

Before conducting any BLE penetration testing, ensure you understand:

1. **Jurisdiction**: BLE testing is subject to local radio frequency regulations and laws
   regarding computer access and electronic communications
2. **Authorization**: Obtain explicit written permission from the device owner before testing
3. **Scope**: Clearly define the scope of authorized testing to avoid unauthorized access

Device Authorization
---------------------

The tools enforce authorization through the scope configuration:

* **Whitelist Approach**: Only test devices explicitly listed in ``scope.authorized_addresses``
* **Pattern Matching**: Use device names or MAC ranges to specify authorized targets
* **Audit Trail**: All tests generate logs identifying tested devices and actions taken

Key Safety Guidelines
---------------------

1. **Test in Isolation**: Conduct tests in RF-isolated environments (Faraday cages) when possible
2. **No Data Exfiltration**: Do not extract or retain personal data from tested devices
3. **Minimal Persistence**: Avoid persistent modifications to tested devices
4. **Safety Timeouts**: All operations enforce configurable timeouts to prevent hanging attacks
5. **Logging and Accountability**: All activities are logged with timestamps and details

Permitted Actions
^^^^^^^^^^^^^^^^^^

* Device discovery and enumeration
* Service and characteristic enumeration
* Pairing procedure testing
* Signal strength and range analysis
* Replay attack detection
* Fuzzing with validation

Prohibited Actions
^^^^^^^^^^^^^^^^^^^

* Testing unauthorized devices
* Causing permanent device damage
* Data exfiltration beyond authorized scope
* Disrupting critical services or safety systems
* Testing medical or safety-critical devices without specialized authorization

Attack Workflows
================

Device Discovery and Enumeration
---------------------------------

**Purpose**: Identify available BLE devices and analyze their characteristics

**Configuration**:

.. code-block:: yaml

    attack:
      type: "scan"
      timeout: 30
    target:
      name_pattern: "*"

**Workflow**:

1. Configure discovery timeout (typically 10-30 seconds)
2. Start device enumeration
3. Collect device information:
   - MAC addresses
   - Device names
   - Advertised services
   - TX power levels
   - Connection status
4. Generate enumeration report

**Report Output**:

The report includes:

* Device inventory with addresses and names
* Discovered services and characteristics
* Signal strength measurements
* Recommended next steps

Pairing Attack Analysis
-----------------------

**Purpose**: Analyze pairing mechanisms for vulnerabilities

**Prerequisites**:

* Device address and name verified
* Authorized for pairing attempts
* Device in discoverable/pairing mode (if required)

**Configuration**:

.. code-block:: yaml

    attack:
      type: "pairing"
      timeout: 20
      retry_on_failure: true
      max_retries: 3
    target:
      address: "AA:BB:CC:DD:EE:FF"

**Workflow**:

1. Attempt standard BLE pairing
2. Analyze pairing mechanism:
   - Out-of-band authentication
   - Just Works pairing
   - PIN/passkey requirements
3. Test for common weaknesses:
   - Weak PIN enforcement
   - Replay vulnerabilities
   - MITM susceptibility
4. Document findings and recommendations

**Findings Interpretation**:

* **PASS**: Device uses secure pairing with adequate validation
* **WARNING**: Device supports deprecated pairing methods
* **CRITICAL**: Device vulnerable to replay or MITM attacks

Man-in-the-Middle Detection
----------------------------

**Purpose**: Detect and document MITM attack feasibility

**Prerequisites**:

* Two BLE adapters (one for monitoring, one for interception)
* Device must be in active communication

**Configuration**:

.. code-block:: yaml

    attack:
      type: "mitm"
      timeout: 60
    target:
      address: "AA:BB:CC:DD:EE:FF"
      service_uuid: "180D"  # Heart Rate Service

**Workflow**:

1. Monitor traffic between client and device
2. Analyze encryption status
3. Attempt connection interception
4. Evaluate traffic encryption and authentication
5. Test for signature verification

**Critical Controls**:

* Limit testing to LAN segments
* Disable testing near production networks
* Verify no real devices connect during testing

Protocol Fuzzing
----------------

**Purpose**: Test protocol robustness through malformed inputs

**Prerequisites**:

* Comprehensive service enumeration completed
* Device supports read/write operations
* Explicit authorization for fuzzing

**Configuration**:

.. code-block:: yaml

    attack:
      type: "fuzzing"
      timeout: 120
    target:
      characteristics:
        - "2A18"  # Body Sensor Location
        - "2A19"  # Heart Rate Control Point

**Workflow**:

1. Define fuzzing parameters:
   - Input ranges
   - Invalid data patterns
   - Edge cases
2. Send malformed data to target characteristics
3. Monitor for:
   - Crashes or disconnections
   - Unexpected behavior
   - Information leakage
4. Document reactions and potential vulnerabilities

**Safety**: Fuzzing includes built-in safeguards:

* Automatic disconnection on error
* Device state restoration
* Configurable intensity levels

Replay Attack Detection
-----------------------

**Purpose**: Identify susceptibility to replay attacks

**Prerequisites**:

* Valid captured commands or characteristics
* Device must be reachable
* Authorization for replay testing

**Configuration**:

.. code-block:: yaml

    attack:
      type: "replay"
      timeout: 30
    target:
      address: "AA:BB:CC:DD:EE:FF"

**Workflow**:

1. Capture characteristic write operations
2. Disconnect from device
3. Reconnect and replay captured operations
4. Analyze device response:
   - Does it accept the replayed command?
   - Is there timestamp/nonce validation?
   - Are sequence numbers checked?
5. Document findings

**Critical Findings**:

* Devices should reject replayed operations
* Commands should include monotonic counters
* Timestamp validation should be enforced

Report Generation and Interpretation
====================================

Report Formats
--------------

The tools support multiple output formats:

**JSON** (Default)
  Machine-readable format suitable for parsing and integration
  
**HTML**
  Human-readable format with navigation and styling
  
**PDF**
  Formatted report suitable for documentation and archival

Generating Reports
-------------------

.. code-block:: bash

    # Generate JSON report
    python -m ble_pentest scan --config config.yaml --output report.json

    # Generate HTML report
    python -m ble_pentest scan --config config.yaml --format html --output report.html

    # Generate PDF report with recommendations
    python -m ble_pentest pairing --config config.yaml --format pdf \
        --include-recommendations --output pairing_analysis.pdf

Report Structure
----------------

Every report includes:

**Executive Summary**
  High-level findings and critical vulnerabilities

**Methodology**
  Attack type, configuration, and scope

**Findings**
  Detailed results organized by severity:
  
  * CRITICAL: Immediate risk to security/safety
  * HIGH: Significant vulnerabilities requiring mitigation
  * MEDIUM: Notable issues with moderate risk
  * LOW: Minor findings or best practice suggestions
  * INFORMATIONAL: Neutral observations

**Detailed Analysis**
  Attack-specific technical details and evidence

**Recommendations**
  Prioritized remediation steps

**Appendices**
  Configuration used, packet captures (if enabled), logs

Interpreting Key Findings
--------------------------

**Weak Pairing Mechanism**
  A device that accepts pairing without strong authentication

  - **Risk**: Unauthorized pairing and control
  - **Recommendation**: Implement PIN/OOB authentication

**Unencrypted Communication**
  Device sends sensitive data without encryption

  - **Risk**: Eavesdropping and data interception
  - **Recommendation**: Enable BLE encryption for all communications

**Missing Authentication**
  Characteristics accept arbitrary writes without validation

  - **Risk**: Unauthorized device control
  - **Recommendation**: Implement proper authentication and authorization

**Replay Vulnerability**
  Device accepts replayed commands

  - **Risk**: Repeated unauthorized actions
  - **Recommendation**: Implement counter or timestamp validation

Scope Limitation and Authorization
===================================

Preventing Unauthorized Testing
--------------------------------

The tools include built-in controls to prevent testing outside the authorized scope:

**Address Whitelisting**

.. code-block:: yaml

    scope:
      authorized_addresses:
        - "AA:BB:CC:DD:EE:FF"
        - "11:22:33:44:55:66"

**Pattern-based Authorization**

.. code-block:: yaml

    scope:
      authorized_names:
        - "TestDevice*"
        - "Lab-*"

**MAC Range Authorization**

.. code-block:: yaml

    scope:
      authorized_ranges:
        - "AA:BB:CC:00:00:00/AA:BB:CC:FF:FF:FF"

**Verification Process**

Before each attack, the tools verify:

1. Target device address is in the whitelist
2. Device name matches authorized patterns
3. Device MAC falls within authorized ranges

If verification fails, the attack is aborted with a clear error message.

Audit and Logging
-----------------

All penetration testing activities are logged to provide accountability:

.. code-block:: yaml

    global:
      log_file: "ble_pentest_audit.log"

Logs include:

* Timestamp of each operation
* Tested device(s) with full details
* Attack type and configuration
* Results and findings
* User or operator identifier

Best Practices
==============

Before Testing
--------------

1. Obtain explicit written authorization from device owner
2. Define clear scope and testing period
3. Review all safety guidelines with team members
4. Test in isolated environment when possible
5. Verify all devices are properly authorized
6. Backup device configurations if needed

During Testing
--------------

1. Monitor device behavior for unexpected issues
2. Have recovery procedures ready (device reset, etc.)
3. Keep team members informed of ongoing tests
4. Document any deviations from plan
5. Stop immediately if unexpected issues occur

After Testing
-------------

1. Verify all tested devices still function correctly
2. Document all findings in comprehensive report
3. Provide recommendations with priority levels
4. Conduct follow-up testing after remediation
5. Archive audit logs and configurations
6. Schedule follow-up assessments

Advanced Topics
===============

Custom Configuration Examples
------------------------------

See ``tools/ble_pentest/examples/`` for:

* ``config_example.yaml`` - Complete annotated configuration
* ``config_minimal.yaml`` - Minimal viable configuration
* ``config_safety_first.yaml`` - Configuration emphasizing safety checks

Sample Report Outputs
---------------------

See ``tools/ble_pentest/examples/reports/`` for:

* ``scan_report_example.json`` - Device enumeration results
* ``pairing_report_example.json`` - Pairing analysis results
* ``fuzzing_report_example.json`` - Fuzzing test results

Troubleshooting
===============

Common Issues
-------------

**Device Not Discovered**
  
  * Verify device is powered on and discoverable
  * Ensure BLE adapter is functioning (check with ``hciconfig``)
  * Verify device address is correct
  * Check signal strength is adequate

**Pairing Fails**

  * Device may require pairing initiation on the device itself
  * Verify pairing is not already established
  * Check for PIN/passkey requirements
  * Ensure device is not in a protected state

**Connection Timeout**

  * Increase timeout value in configuration
  * Verify device is responsive
  * Check for interference from other wireless devices
  * Try reducing testing intensity or range

**Fuzzing Causes Crashes**

  * Reduce fuzzing intensity in configuration
  * Use validated fuzzing payloads first
  * Add error handling and timeouts
  * Test with non-critical devices first

Getting Help
------------

* Check configuration files in ``tools/ble_pentest/examples/``
* Review logs in detail for error messages
* Ensure all prerequisites are installed
* Verify device is functioning with official tools
* Consult platform-specific BLE documentation

See Also
========

* `Bleak Documentation <https://bleak.readthedocs.io/>`_
* `Frida Documentation <https://frida.re/docs/>`_
* `BLE Specification <https://www.bluetooth.com/specifications/>`_
* :doc:`/dev-guide/development-environment`
* :doc:`/dev-guide/architecture`
