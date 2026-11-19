// ORIGIN: copied unchanged (except this line) from FHSS-Link/rtl/hop_engine/rtl/hop_keyed.v (own design). For reading in labs 3-6; the kit does not simulate RTL.
// NOTE: this RTL reduces the digest with a Lemire unbiased reduction on 32-bit chunks (and has a retry byte in the message).
// The Python models in the kit use hop = digest mod 13 of an 8-byte counter, as in FHSS-Link/lab4/silicon. The two agree on all
// properties the labs teach (leakage points, state registers, output statistics); see docs/MODEL_NOTES.md.
// hop_keyed.v - keyed hop engine for FHSS-Link: SipHash-2-4 PRF + Lemire unbiased reduction.
// Verilog-2001 subset (iverilog / verilator / yosys). One SipRound per clock (iterative core).
//
//   digest  = SipHash-2-4(key[127:0], {retry[7:0], slot[55:0]})      (8 rounds, 64-bit message word)
//   channel = Lemire(chunk of digest, M), chunks taken LSB first; if all NCH chunks are rejected, retry++ and re-hash.
//
// Protocol: load key (key_we) and slot (slot_we) while idle; pulse req; wait for valid (1 clk pulse, chan valid then).
// The internal slot counter auto-increments on every completed hop (wraps mod 2^56).
// Cycle count: req -> valid is 12 clocks (typical) + 11 per rare retry (see README).
/* verilator lint_off UNUSEDSIGNAL */
module hop_keyed #(
    parameter M   = 13,           // number of channels (>= 2)
    parameter RW  = 32,           // reduction word width (bits of digest consumed per attempt)
    parameter NCH = 2,            // attempts per digest (NCH <= 4, NCH*RW <= 64). RW=8,NCH=1 is a TEST config that exercises retries
    parameter RIPPLE = 0,         // 0: '+' operator (synthesis tool picks adder), 1: explicit ripple-carry adders (area-lean, slower)
    parameter CW  = $clog2(M)     // channel index width
)(
    input  wire          clk,
    input  wire          rst_n,   // synchronous, active low (control state only)
    input  wire [127:0]  key_in,
    input  wire          key_we,
    input  wire [55:0]   slot_in,
    input  wire          slot_we,
    input  wire          req,
    output wire          busy,
    output reg           valid,
    output reg  [CW-1:0] chan
);
    localparam [2:0] S_IDLE = 3'd0, S_LOAD = 3'd1, S_RND = 3'd2, S_FIN = 3'd3, S_RED = 3'd4;
    localparam [63:0] C0 = 64'h736f6d6570736575, C1 = 64'h646f72616e646f6d,
                      C2 = 64'h6c7967656e657261, C3 = 64'h7465646279746573;
    localparam [63:0] BLK = 64'h0800000000000000;            // length byte (8) << 56 : final block of an 8-byte message
    localparam [RW:0]   TWO_RW = {1'b1, {RW{1'b0}}};
    localparam [RW:0]   THR = TWO_RW % M;                     // 2^RW mod M (< M <= 2^RW), elaboration-time constant

    reg [127:0] key_r;
    reg [55:0]  slot_r;
    reg [7:0]   retry;
    reg [2:0]   state;
    reg [2:0]   stp;
    reg [1:0]   cnt;
    reg [63:0]  v0, v1, v2, v3;

    wire [63:0] msg = {retry, slot_r};
    assign busy = (state != S_IDLE);

    // ripple-carry adder (used when RIPPLE=1)
    function [63:0] radd;
        input [63:0] a, b;
        integer i; reg c;
        begin
            c = 1'b0;
            for (i = 0; i < 64; i = i + 1) begin
                radd[i] = a[i] ^ b[i] ^ c;
                c = (a[i] & b[i]) | (c & (a[i] ^ b[i]));
            end
        end
    endfunction

    // ---- one SipRound (combinational) ----
    wire [63:0] a0 = RIPPLE ? radd(v0, v1) : (v0 + v1);
    wire [63:0] a1 = {v1[50:0], v1[63:51]} ^ a0;               // rotl13(v1) ^ a0
    wire [63:0] a0r = {a0[31:0], a0[63:32]};                   // rotl32(a0)
    wire [63:0] a2 = RIPPLE ? radd(v2, v3) : (v2 + v3);
    wire [63:0] a3 = {v3[47:0], v3[63:48]} ^ a2;               // rotl16(v3) ^ a2
    wire [63:0] b0 = RIPPLE ? radd(a0r, a3) : (a0r + a3);
    wire [63:0] b3 = {a3[42:0], a3[63:43]} ^ b0;               // rotl21(a3) ^ b0
    wire [63:0] b2 = RIPPLE ? radd(a2, a1) : (a2 + a1);
    wire [63:0] b1 = {a1[46:0], a1[63:47]} ^ b2;               // rotl17(a1) ^ b2
    wire [63:0] b2r = {b2[31:0], b2[63:32]};                   // rotl32(b2)
    wire [63:0] r0 = b0, r1 = b1, r2 = b2r, r3 = b3;

    // ---- Lemire reduction of the low RW bits of v0 ----
    wire [RW-1:0]      x    = v0[RW-1:0];
    localparam [CW:0]  MC   = M;
    wire [RW+CW:0]     prod = x * MC;                          // x < 2^RW, M <= 2^CW  ->  prod < 2^(RW+CW)
    wire [RW-1:0]      lo   = prod[RW-1:0];
    wire [CW-1:0]      hi   = prod[RW+CW-1:RW];
    wire               acc  = ({1'b0, lo} >= THR);

    always @(posedge clk) begin
        valid <= 1'b0;
        if (key_we)  key_r  <= key_in;
        if (slot_we) slot_r <= slot_in;
        if (!rst_n) begin
            state <= S_IDLE;
        end else begin
            case (state)
            S_IDLE: if (req) begin retry <= 8'd0; state <= S_LOAD; end
            S_LOAD: begin
                v0 <= key_r[63:0]   ^ C0;
                v1 <= key_r[127:64] ^ C1;
                v2 <= key_r[63:0]   ^ C2;
                v3 <= key_r[127:64] ^ C3 ^ msg;                // v3 ^= m folded into load
                stp <= 3'd0; state <= S_RND;
            end
            S_RND: begin
                stp <= stp + 3'd1;
                case (stp)
                3'd1:    begin v0 <= r0 ^ msg; v1 <= r1; v2 <= r2; v3 <= r3 ^ BLK; end   // end of c-rounds for m ; absorb final block
                3'd3:    begin v0 <= r0 ^ BLK; v1 <= r1; v2 <= r2 ^ 64'hff; v3 <= r3; end // end of c-rounds for final block ; v2 ^= 0xff
                default: begin v0 <= r0; v1 <= r1; v2 <= r2; v3 <= r3; end
                endcase
                if (stp == 3'd7) state <= S_FIN;
            end
            S_FIN: begin
                v0 <= v0 ^ v1 ^ v2 ^ v3;                        // 64-bit digest
                cnt <= 2'd0; state <= S_RED;
            end
            S_RED: begin
                if (acc) begin
                    chan <= hi; valid <= 1'b1; state <= S_IDLE;
                    slot_r <= slot_r + 56'd1;
                end else if (cnt == NCH-1) begin
                    retry <= retry + 8'd1; state <= S_LOAD;
                end else begin
                    v0 <= v0 >> RW; cnt <= cnt + 2'd1;
                end
            end
            default: state <= S_IDLE;
            endcase
        end
    end

`ifdef FORMAL
    // formal properties (SymbiYosys): not part of synthesis or simulation builds
    reg f_init = 1'b1; reg f_pv = 1'b0; reg [2:0] f_ps = 3'd0; reg [55:0] f_pslot = 56'd0; reg f_pwe = 1'b0;
    always @(posedge clk) begin f_init <= 1'b0; f_pv <= valid; f_ps <= state; f_pslot <= slot_r; f_pwe <= slot_we; end
    always @* if (f_init) assume(!rst_n);                       // start from reset
    always @* if (busy) assume(!key_we && !slot_we);            // protocol: key/slot are loaded only while idle
    always @* if (busy) assume(!req);                           // protocol: req only while idle
    always @(posedge clk) if (!f_init) begin
        assert(state <= S_RED);                                 // FSM never leaves its 5 legal states
        if (state == S_RND) assert(stp <= 3'd7);
        if (state == S_RED) assert(cnt < NCH);
        if (valid) assert(chan < M);                            // unbiased reduction output is always a legal channel
        assert(!(valid && f_pv));                               // single-clock valid pulse
        if (valid) assert(f_ps == S_RED && state == S_IDLE);    // valid only follows the reduction state
        if (valid) assert(slot_r == f_pslot + 56'd1);           // slot counter advances by exactly one per delivered hop
        if (!valid && f_ps != S_RED && !f_pwe) assert(slot_r == f_pslot);   // ... and never otherwise
    end
    always @(posedge clk) cover(!f_init && valid && f_ps == S_RED && retry == 8'd0);   // a normal hop is reachable
`endif
endmodule
