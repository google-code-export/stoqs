function [extra]=extract_points(model,insit)
%
%
%  Usage
%
%   Get the value for the nearest node of the model to the insitu
%   measurement. It's use in the function model_vs_stoqs
%
% Input
%   
%   Model= Model information getting from model_vs_stoqs
%   insit= Insitu measuremente getting from model_vs_stoqs
%
% Ouput
%   extra = Structure with the x,y index(indx,indy), the data model value(pointdata).
%        Get one model output for every insitudata
%           .pointdata = Value of the nearest node to the insitu data                        
%           .indx,indy = Index of the node nearest to the insitu data
%           .modeltime = Model time.
%           .time = Time of each of the in situ measurement
%           
%


if isempty(insit.vari)
  extra.pointdata(1)=NaN;
  extra.indx(1)=NaN;
  extra.indy(1)=NaN;
  extra.lat(1)=NaN;
  extra.lon(1)=NaN;
  extra.modeltime(1)=model.date;

else

 for i=1:length(insit.long)
  [inde,dist]=near(insit.long(i),model.lon);
  indy=inde;clear inde;
  [inde,dist]=near(insit.lati(i),model.lat);
  indx=inde;clear inde;
  extra.pointdata(i)=model.data_inlevel(indx,indy);
  extra.indx(i)=indx;
  extra.indy(i)=indy;
  extra.modeltime(i)=model.date;
  extra.lat(i)=model.lat(indx);
  extra.lon(i)=model.lon(indy);
 
 end



end

    