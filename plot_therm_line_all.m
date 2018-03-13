% Plots data from all different temperatures when data is stored in
% directory tree with each folder holding scans from a specific temperature

num_scans = 1000;   % Number of scans to plot
therm_dat = 1:1000; % rows thermal data is in


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
    load([full_path,scans(1).name])
    
    % Create new array where columns equal to zero have been removed
    arr = arr(:,therm_dat);
    arr_mod = arr(any(arr,2),:);
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
end

xlabel('Scan direction [aribtrary unit]')
ylabel('Temperature [^oC]')
legend(plots, temp_str)
