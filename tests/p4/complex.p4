/* -*- P4_16 -*- */

/*
 * complex.p4 : A P4 program that tries to exercise as many features of the
 * P4 language as possible. There is a separate program expr.p4 for
 * exercising all expressions.
 *
 * The P4 code is "inspired" by a traditional IP router, to make it easy  to
 * follow the code. That said, this is not intended to be a realistic or
 * feature complete or even correct IP router. This is just a test program
 * to exercise as many of the P4 language features as possible.
 */

#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;

header ethernet_t {
    bit<48> dst_addr;
    bit<16> ethertype;
}

header ipv4_header_t {
    bit<32> dst_addr;
    bit<8> ttl;
}

struct metadata_t { }

struct headers_t {
    ethernet_t ethernet;
    ipv4_header_t ipv4;
}

parser PacketParser(
    packet_in packet,
    out headers_t headers,
    inout metadata_t metadata,
    inout standard_metadata_t standard_metadata
) {

    state start {
        packet.extract(headers.ethernet);
        transition select(headers.ethernet.ethertype) {
            TYPE_IPV4: ipv4;
            default: accept;
        }
    }

    state ipv4 {
        packet.extract(headers.ipv4);
        transition accept;
    }

}

control PacketVerifyChecksum(inout headers_t headers, inout metadata_t metadata) {
    apply {  }
}

control ProcessIngressIPv4(
    inout headers_t headers,
    inout metadata_t metadata,
    inout standard_metadata_t standard_metadata
) {
    action act_miss() {
        mark_to_drop(standard_metadata);
    }

    action act_hit(bit<9> out_port) {
        standard_metadata.egress_spec = out_port;
    }

    table ethernet_ipv4_fib {
        key = {
            headers.ethernet.dst_addr: exact;
            headers.ipv4.dst_addr: lpm;
        }
        actions = {
            act_hit;
        }
    }

    table ipv4_fib {
        key = {
            headers.ipv4.dst_addr: lpm;
        }
        actions = {
            act_hit;
        }
        const entries = {
            32w0x0a010000 &&& 32w0xffff0000: act_hit(3);   // 10.1.0.0/16 -> 3
            32w0x0a000000 &&& 32w0xff000000: act_hit(4);   // 10.0.0.0/8  -> 4
        }
    }

    table ttl_tbl {
        key = {
            headers.ipv4.ttl: range;
        }
        actions = {
            act_miss;
        }
        const entries = {
            100..150: act_miss();
        }
    }

    apply {
        if (headers.ipv4.isValid()) {
            if (ethernet_ipv4_fib.apply().miss) {
                if (ipv4_fib.apply().miss) {
                    act_miss();
                } else {
                    ttl_tbl.apply();
                }
            }
        }
    }
}

control ProcessIngress(
    inout headers_t headers,
    inout metadata_t metadata,
    inout standard_metadata_t standard_metadata
) {
    ProcessIngressIPv4() process_ingress_ipv4;
    bit<1> goto_ipv4;

    action act_miss() {
        goto_ipv4 = (bit<1>)1;
    }

    action act_hit(bit<9> out_port) {
        standard_metadata.egress_spec = out_port;
        goto_ipv4 = (bit<1>)0;
    }

    table ethernet_fib {
        key = {
            headers.ethernet.dst_addr: exact;
        }
        actions = {
            act_miss;
            act_hit;
        }
        const default_action = act_miss();
    }

    table ethernet_ethertype_fib {
        key = {
            headers.ethernet.dst_addr: exact;
            headers.ethernet.ethertype: exact;
        }
        actions = {
            act_miss;
            act_hit;
        }
        const default_action = act_miss();
    }

    apply {
        if (headers.ethernet.isValid()) {
            switch (ethernet_fib.apply().action_run) {
                act_miss: {
                    ethernet_ethertype_fib.apply();
                }
            }

            if ((goto_ipv4 == 1) && headers.ipv4.isValid()) {
                process_ingress_ipv4.apply(headers, metadata, standard_metadata);
            } else {
                mark_to_drop(standard_metadata);
            }
        }
    }
}

control ProcessEgress(
    inout headers_t headers,
    inout metadata_t metadata,
    inout standard_metadata_t standard_metadata
) {
    apply { }
}

control PacketComputeChecksum(inout headers_t headers, inout metadata_t metadata) {
    apply { }
}

control PacketDeparser(packet_out packet, in headers_t headers) {
    apply {
        packet.emit(headers.ethernet);
        packet.emit(headers.ipv4);
    }
}

V1Switch(
    PacketParser(),
    PacketVerifyChecksum(),
    ProcessIngress(),
    ProcessEgress(),
    PacketComputeChecksum(),
    PacketDeparser()
) main;
