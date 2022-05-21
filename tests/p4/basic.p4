/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

header action_t {
    bit<32> action_id;
}

header test_t {
    bit<8> value;
}

struct metadata {
}

struct headers {
    action_t act;
    test_t test;
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
        packet.extract(hdr.act);
        transition select(hdr.act.action_id) {
            0: accept;
            default: parse_test;
        }
    }

    state parse_test {
        packet.extract(hdr.test);
        transition accept;
    }

}

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(
    inout headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata
) {
    action act_add_header() {
        hdr.test.setValid();
    }

    action act_remove_header() {
        hdr.test.setInvalid();
    }

    action act_assign() {
        hdr.test.value = 0xaa;
    }

    action act_extern() {
        mark_to_drop(standard_metadata);
    }

    action act_extern_keyword() {
        assert(hdr.test.value == 0xaa);
        hdr.test.value = 0xbb;
    }

    table operations {
        key = {
            hdr.act.action_id: exact;
        }
        actions = {
            act_add_header;
            act_remove_header;
            act_assign;
            act_extern;
            act_extern_keyword;
        }
        const entries = {
            0: act_add_header();
            1: act_remove_header();
            2: act_assign();
            3: act_extern();
            4: act_extern_keyword();
        }
    }

    apply {
        if (hdr.act.isValid()) {
            operations.apply();
            standard_metadata.egress_spec = standard_metadata.ingress_port;
        }
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
    apply {  }
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
        packet.emit(hdr.act);
        packet.emit(hdr.test);
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
