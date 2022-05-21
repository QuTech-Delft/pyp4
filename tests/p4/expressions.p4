/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

header expr_t {
    bit<32> in32a;
    bit<32> in32b;
    bit<8> in8;
    bit<1> in1;
    bit<32> out32;
    bit<1> out1;
    bit<8> op;
    bit<6> padding;
}

struct metadata {
    bool flag1;
}

struct headers {
    expr_t expr;
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
        packet.extract(hdr.expr);
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
    action act_drop() {
        mark_to_drop(standard_metadata);
    }

    action act_add() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = hdr.expr.in32a + hdr.expr.in32b;
    }

    action act_subtract() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = hdr.expr.in32a - hdr.expr.in32b;
    }

    action act_multiply() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = hdr.expr.in32a * hdr.expr.in32b;
    }

    action act_left_shift() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = hdr.expr.in32a << hdr.expr.in8;
    }

    action act_right_shift() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = hdr.expr.in32a >> hdr.expr.in8;
    }

    action act_is_equal() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        if (hdr.expr.in32a == hdr.expr.in32b)
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_is_not_equal() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        if (hdr.expr.in32a != hdr.expr.in32b)
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_is_greater_than() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        if (hdr.expr.in32a > hdr.expr.in32b)
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_is_greater_than_or_equal() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        if (hdr.expr.in32a >= hdr.expr.in32b)
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_is_less_than() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        if (hdr.expr.in32a < hdr.expr.in32b)
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_is_less_than_or_equal() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        if (hdr.expr.in32a <= hdr.expr.in32b)
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_logical_and() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        if (hdr.expr.in32a < 10 && hdr.expr.in32b < 10)
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_logical_or() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        if (hdr.expr.in32a < 10 || hdr.expr.in32b < 10)
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_logical_not() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // Redundant boolean check as otherwise compiler is too clever and optimises the ! away
        if (!((hdr.expr.in32a < 10) && (hdr.expr.in32a < 10)))
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_bitwise_and() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = hdr.expr.in32a & hdr.expr.in32b;
    }

    action act_bitwise_or() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = hdr.expr.in32a | hdr.expr.in32b;
    }

    action act_bitwise_xor() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = hdr.expr.in32a ^ hdr.expr.in32b;
    }

    action act_bitwise_not() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = ~hdr.expr.in32a;
    }

    action act_is_valid() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_is_valid_union() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_data_to_bool() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // The P4 compiler generates a d2b call for the isValid() call.
        if (hdr.expr.isValid())
            hdr.expr.out1 = 1;
        else
            hdr.expr.out1 = 0;
    }

    action act_bool_to_data() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // Even though flag1 is a bool, the P4 compiler generates a b2d
        // operator call.
	meta.flag1 = (hdr.expr.in1 == 1);
        hdr.expr.out1 = (bit<1>)(meta.flag1);
    }

    action act_bool() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // Logical OR with true should create a bool expression.
        if ((hdr.expr.in1 == 1) || true)
            hdr.expr.out1 = 1;
    }

    action act_two_comp_mod() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_sat_cast() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_usat_cast() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_ternary() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_deref_header_stack() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_last_stack_index() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_size_stack() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_access_field() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_dereference_union_stack() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_access_union_header() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        // TODO
    }

    action act_runtime_data(bit<32> runtime_data) {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        hdr.expr.out32 = runtime_data;
        // TODO
    }

    register<bit<32>>(1) reg;

    action act_value() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;
        reg.write((bit<32>)0, 0xbe);
        reg.read(hdr.expr.out32, (bit<32>)0);
    }

    action act_log_msg() {
        log_msg("Hello, world! in1={}; in8={};", {hdr.expr.in1, hdr.expr.in8});
    }

    table operations {
        key = {
            hdr.expr.op: exact;
        }
        actions = {
            act_drop;
            act_add;
            act_subtract;
            act_multiply;
            act_left_shift;
            act_right_shift;
            act_is_equal;
            act_is_not_equal;
            act_is_greater_than;
            act_is_greater_than_or_equal;
            act_is_less_than;
            act_is_less_than_or_equal;
            act_logical_and;
            act_logical_or;
            act_logical_not;
            act_bitwise_and;
            act_bitwise_or;
            act_bitwise_xor;
            act_bitwise_not;
            act_is_valid;
            act_is_valid_union;
            act_data_to_bool;
            act_bool_to_data;
            act_bool;
            act_two_comp_mod;
            act_sat_cast;
            act_usat_cast;
            act_ternary;
            act_deref_header_stack;
            act_last_stack_index;
            act_size_stack;
            act_access_field;
            act_dereference_union_stack;
            act_access_union_header;
            act_runtime_data;
            act_value;
            act_log_msg;
        }
        const default_action = act_drop();
        const entries = {
            0: act_drop();
            1: act_add();
            2: act_subtract();
            3: act_multiply();
            4: act_left_shift();
            5: act_right_shift();
            6: act_is_equal();
            7: act_is_not_equal();
            8: act_is_greater_than();
            9: act_is_greater_than_or_equal();
            10: act_is_less_than();
            11: act_is_less_than_or_equal();
            12: act_logical_and();
            13: act_logical_or();
            14: act_logical_not();
            15: act_bitwise_and();
            16: act_bitwise_or();
            17: act_bitwise_xor();
            18: act_bitwise_not();
            19: act_is_valid();
            20: act_is_valid_union();
            21: act_data_to_bool();
            22: act_bool_to_data();
            23: act_bool();
            24: act_two_comp_mod();
            25: act_sat_cast();
            26: act_usat_cast();
            27: act_ternary();
            28: act_deref_header_stack();
            29: act_last_stack_index();
            30: act_size_stack();
            31: act_access_field();
            32: act_dereference_union_stack();
            33: act_access_union_header();
            34: act_runtime_data(0xaa);
            35: act_value();
            36: act_log_msg();
        }
    }

    apply {
        if (hdr.expr.isValid()) {
            operations.apply();
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
        packet.emit(hdr.expr);
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
