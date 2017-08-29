db_file_loc = 'C:\Users\Joseph Farah\Documents\lppc_internship_files\lvms\anubis\db_loc.txt';
db_file_ID = fopen(db_file_loc, 'r');
file_name = fgetl(db_file_ID);
display(file_name);


ip = '128.103.100.25';
connected = 0;
connectAttempt = 1;
maxAttempt = 10;
fileID = fopen(strcat('C:\Users\Joseph Farah\Documents\lppc_internship_files\lvms\anubis\',file_name),'wt');
fmt = '%s\n';

lvms_obj = instrfind('Type', 'tcpip', 'RemoteHost', ip, 'RemotePort', 3490, 'Tag', '');
if isempty(lvms_obj)
    lvms_obj = tcpip(ip, 3490);
else
   lvms_obj = lvms_obj(1);   
end
display('Connection hopefully made');

while (connectAttempt < maxAttempt) && not(connected);
    try
        fopen(lvms_obj);
        connected = 1; 
    catch err
       connectAttempt = connectAttempt + 1;
        disp(['HV Meter connection attempt ',num2str(connectAttempt)]);
        connected = 0; 
        continue;
    end
end

while 1
    c = strcat(",", mat2str(clock));
    fprintf(lvms_obj, ':init');
    fprintf(lvms_obj, '*trg');
    fprintf(lvms_obj, 'fetch?');
    fprintf(fileID,fmt,strcat(fscanf(lvms_obj), c));
end


fclose(lvms_obj);
fclose(fileID);
clear lvms_obj;