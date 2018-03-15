% Plots data from all different temperatures when data is stored in
% directory tree with each folder holding scans from a specific temperature
% close all 
clear all

calibrate = true;    % Whether to scale temperatures by calibration
poly_fit = [1.629244451846427,-17.899113249750750];

num_scans = 1000;   % Number of scans to plot
therm_dat = 1:1000; % rows thermal data is in

% extract_range = 350:500;    % Columns we want to extract for temperature calibration - 14/03/2018
extract_range = 580:640;    % Columns extracted for Matt's LSP (not cooled) 09/03/2018

pathname = uigetdir('C:\Users\tw9616\Documents\PhD\EE Placement\Therm_Lidar Python\',...
    'Select directory for LSP scans');
all_dirs = dir([pathname,'\*oC']);
dir_flag = [all_dirs.isdir];
temp_dirs = all_dirs(dir_flag);

my_colours = hsv(length(temp_dirs));
plots = [];

figure()
for i=1:length(temp_dirs)
    dir_string = temp_dirs(i).name;
    full_path = [pathname,'\',dir_string,'\'];
    scans = dir([full_path,'*.mat']);
    if length(scans) < 1
        continue
    end
    load([full_path,scans(1).name])
    
    % Create new array where columns equal to zero have been removed
    arr = arr(:,therm_dat);
    arr_mod = arr(any(arr,2),:);   % Removing columns at zero
    
    % Calibrate array
    if calibrate == true 
        arr_mod = (arr_mod - poly_fit(2)) / poly_fit(1);
    end
    
    mean_temps = mean(arr_mod,1);
    min_temps = min(arr_mod);
    max_temps = max(arr_mod);
    std_temps = 2 * std(arr_mod);  % k=2 standard deviation
    
    
    p = plot(mean_temps, 'color', my_colours(i,:), 'linewidth', 2);
    plots = [plots p];
    
    if i==1
        hold on
        grid on
    end
%     plot(min_temps, 'color', my_colours(i,:), 'linewidth', 1)
%     plot(max_temps, 'color', my_colours(i,:), 'linewidth', 1)
%     shade = [min_temps, fliplr(max_temps)];
    shade = [mean_temps-std_temps, fliplr(mean_temps+std_temps)];
    f1 = fill([therm_dat fliplr(therm_dat)], shade, my_colours(i,:));
    set(f1,'linestyle', 'none')
    alpha(f1, 0.5)
    
    temp_str{i} = regexprep(dir_string,'oC','');
    
    % ---------------------------------------------------------------------
    % Temperature calibration
    mean_temp(i,1) = str2num(temp_str{i});
    mean_temp(i,2) = mean(mean_temps(extract_range));
    
    mean_std(i,1) = str2num(temp_str{i});
    mean_std(i,2) = mean(std_temps(extract_range));
    % ---------------------------------------------------------------------
end

xlabel('Scan direction [aribtrary unit]')
ylabel('Temperature [^oC]')
legend(plots, temp_str)

% -------------------------------------------------------------------------
% Calibration
poly_order = 1;

mean_temp = sortrows(mean_temp);
fit = polyfit(mean_temp(:,1), mean_temp(:,2), poly_order);
eval = polyval(fit, mean_temp(:,1));

figure;
plot(mean_temp(:, 1), mean_temp(:,2), 'x', 'markersize', 10, 'linewidth',2)
hold on
plot(mean_temp(:,1), eval, 'linestyle','-', 'linewidth', 2)
ylabel('Retrieved temperature [^oC]')
xlabel('Temeprature [^oC]')
title(sprintf('Temperature calibration and fit for polynomial n=%i', poly_order))

residuals = eval - mean_temp(:,2);
figure;
plot(mean_temp(:,1),residuals, 'x', 'markersize', 10, 'linewidth', 2)
ylabel('Fit residuals [^oC]')
xlabel('Temeprature [^oC]')
title(sprintf('Fit residuals for polynomial n=%i', poly_order))
% -------------------------------------------------------------------------
