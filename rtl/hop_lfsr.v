// ORIGIN: copied unchanged (except this line) from FHSS-Link/rtl/hop_engine/rtl/hop_lfsr.v (own design). For reading in lab 1; the kit does not simulate RTL.
// hop_lfsr.v - 16-bit LFSR reference hop engine (x^16+x^14+x^13+x^11+1, Fibonacci, shift right), hop = state mod M.
// Matches sim/link_sim.py lfsr_hops: step first, then output state % M. Seed 0 is mapped to 1 (lock-up state).
// req -> valid is 1 clock (chan registered).
module hop_lfsr #(
    parameter M  = 13,
    parameter CW = $clog2(M)
)(
    input  wire          clk,
    input  wire          rst_n,
    input  wire [15:0]   seed_in,
    input  wire          seed_we,
    input  wire          req,
    output reg           valid,
    output reg  [CW-1:0] chan
);
    reg [15:0] s;
    wire       fb = s[0] ^ s[2] ^ s[3] ^ s[5];
    wire [15:0] sn = {fb, s[15:1]};
    /* verilator lint_off UNUSEDSIGNAL */
    wire [15:0] md = sn % M;                        // upper bits are always 0 (value < M)
    /* verilator lint_on UNUSEDSIGNAL */
    always @(posedge clk) begin
        valid <= 1'b0;
        if (!rst_n) s <= 16'hACE1;
        else if (seed_we) s <= (seed_in == 16'd0) ? 16'd1 : seed_in;
        else if (req) begin
            s <= sn; chan <= md[CW-1:0]; valid <= 1'b1;
        end
    end

`ifdef FORMAL
    // formal properties (SymbiYosys): not part of synthesis or simulation builds
    reg f_init = 1'b1;
    always @(posedge clk) f_init <= 1'b0;
    always @* if (f_init) assume(!rst_n);                       // start from reset
    always @(posedge clk) if (!f_init) begin
        assert(s != 16'd0);                                     // LFSR never reaches the all-zero lock-up state
        if (valid) assert(chan < M);                            // channel index always in range
    end
`endif
endmodule
