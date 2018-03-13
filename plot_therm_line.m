% Plot lines of thermal data

num_lines = 1000;     % Number of lines to plot
therm_dat = 1:1000; % rows thermal data is in

incr_col = 1/num_lines;

figure()
for i=1:num_lines
    plot(arr(i, therm_dat), 'color', [i*incr_col, 0.5, 0.5])
    if i == 1
        hold on
    end
end
xlabel('Scan point')
ylabel('Temperature [^oC]')