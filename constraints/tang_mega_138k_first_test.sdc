# CPU v0.1 I24-S02 Tang Mega 138K first-test timing constraints.
create_clock -name board_clk_i -period 40.000 [get_ports {board_clk_i}]
set_false_path -from [get_ports {board_reset_n_i}]
