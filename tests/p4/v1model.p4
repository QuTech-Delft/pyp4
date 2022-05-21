/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

#define MAX_PORTS 8

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

typedef bit<48> time_t;

header ping_t {
    bit<32> count;
    time_t last_time;
    time_t cur_time;
}

struct metadata {
    /* empty */
}

struct headers {
    ping_t ping;
}

/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(
    packet_in packet,
    out headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata
) {

    state start {
        packet.extract(hdr.ping);
        transition accept;
    }

}

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(
    inout headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata
) {
    action drop() {
        mark_to_drop(standard_metadata);
    }

    action pass() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
    }

    table tbl_ping {
        key = {
            hdr.ping.count: exact;
        }
        actions = {
            pass;
            drop;
        }
        const default_action = pass();
    }

    apply {
        assume(hdr.ping.isValid());
        assert(hdr.ping.count < 2000);
        log_msg("hdr.ping.count = {}", {hdr.ping.count});
        tbl_ping.apply();
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(
    inout headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata
) {
    // Count the number of received packets
    register<bit<32>>(MAX_PORTS) ping_count_reg;
    // Time last packet was recieved
    register<time_t>(MAX_PORTS) last_time_reg;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action pass() {
        bit<32> ping_count;
        time_t last_time;
        time_t cur_time = standard_metadata.egress_global_timestamp;

        // Increment ping count for this port
        @atomic {
            ping_count_reg.read(ping_count, (bit<32>)standard_metadata.egress_port);
            ping_count = ping_count + 1;
            ping_count_reg.write((bit<32>)standard_metadata.egress_port, ping_count);
        }

        hdr.ping.count = ping_count;

        last_time_reg.read(last_time, (bit<32>)standard_metadata.egress_port);
        last_time_reg.write((bit<32>)standard_metadata.egress_port, cur_time);

        hdr.ping.last_time = last_time;
        hdr.ping.cur_time = cur_time;
    }

    table tbl_ping {
        key = {
            hdr.ping.count: exact;
        }
        actions = {
            pass;
            drop;
        }
        const default_action = pass();
    }

    apply {
        if (hdr.ping.isValid()) {
            tbl_ping.apply();
        }
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
    apply { }
}

/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ping);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
