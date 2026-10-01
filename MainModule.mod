MODULE MainModule
    TASK PERS tooldata suckTool:=[TRUE,[[84.0867,-36.8993,182.989],[1,0,0,0]],[1.1,[20,20,25],[1,0,0,0],0,0,0]];
    TASK PERS wobjdata arucoWobj:=[FALSE,TRUE,"",[[758.413,348.586,379.768],[0.707032,-0.0107152,0.0107349,-0.707019]],[[0,0,0],[1,0,0,0]]];
	TASK PERS wobjdata assWobj:=[FALSE,TRUE,"",[[655.92,-169.184,391.001],[0.707122,-6.0474E-06,-2.1189E-05,-0.707092]],[[0,0,0],[1,0,0,0]]];
    
    CONST robtarget pHome:=[[545.16,-27.39,596.23],[0.00418528,0.952745,-0.303727,-0.00295551],[-1,-1,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget pCircle:=[[39.47,38.40,-0.50],[0.00507756,0.888435,0.458974,0.000893295],[-1,-1,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
	CONST robtarget pSquare:=[[44.71,169.58,-4.79],[0.00510597,0.88839,0.45906,0.00094232],[-1,-1,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
	CONST robtarget pStar:=[[99.99,108.99,-3.22],[0.00507971,0.888409,0.459024,0.00091317],[-1,-1,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
	
    VAR robtarget pPick:=[[781.54,96.22,463.35],[0.00416346,0.952745,-0.303729,-0.00296607],[0,-1,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    
    VAR robtarget pTarget;
    
    VAR string Server_message;
    VAR string client_message;
    
    VAR bool flag := TRUE;
    
    VAR num shapeSelection;
    VAR num colorSelection;
    
    VAR num xPos;
    VAR num yPos;
    VAR num zPos;
    
    VAR num anglex;
    VAR num angley;
    VAR num anglez;
    
    VAR bool ok;
    VAR num positionArray{4};
    
    VAR string selectedObject;
	PROC main()
		IF flag = TRUE THEN
            RobotAsClientConnect;
        ENDIF
        
        selectedObject := "";
        
        flag := FALSE;
        
        Server_message:=RobotClientReciveMessage();
        
        MoveJ pHome, v100, z50, suckTool\WObj:=wobj0;
        
        IF Server_message = "Which Object?" THEN
            TPReadFK shapeSelection, "Choose a shape please!", "Circle", "Square", "Star", stEmpty, stEmpty;
        ENDIF
        
        TPReadFK colorSelection, "Choose a color please!", "Black", "Blue", "Green", "Red", stEmpty;
        
        TEST colorSelection
            CASE 1:
                selectedObject := selectedObject + "Black ";
            CASE 2:
                selectedObject := selectedObject + "Blue ";
            CASE 3:
                selectedObject := selectedObject + "Green ";
            CASE 4:
                selectedObject := selectedObject + "Red ";
            DEFAULT:
        ENDTEST
        
        TEST shapeSelection
            CASE 1:
                selectedObject := selectedObject + "Circle";
            CASE 2:
                selectedObject := selectedObject + "Square";
            CASE 3:
                selectedObject := selectedObject + "Star";
            DEFAULT:
        ENDTEST
        
        RobotClienSendMessage(selectedObject);
        
        IF shapeSelection = 1 THEN
            pTarget := pCircle;
        ELSEIF shapeSelection = 2 THEN
            pTarget := pSquare;
        ELSEIF shapeSelection = 3 THEN
            pTarget := pStar;
        ENDIF
        
        Server_message:=RobotClientReciveMessage();
        
        IF Server_message <> "Not found!" THEN
            ok := StrToVal(Server_message, positionArray);
        
            xPos := positionArray{1};
            yPos := positionArray{2};
            zPos := positionArray{3};
            
            
            pPick.trans.x := xPos;
            pPick.trans.y := yPos;
            pPick.trans.z := zPos;
            
            anglex := EulerZYX(\X, pPick.rot);
            angley := EulerZYX(\Y, pPick.rot);
            anglez := EulerZYX(\Z, pPick.rot);
            
            MoveJ Offs(pPick, 0, 0, 40), v100, z50, suckTool\WObj:=arucoWobj; 
            MoveL pPick, v100, z50, suckTool\WObj:=arucoWobj;
!            WaitDI diOkButton, 1;
            WaitTime 1.5;
            SetDO doValet2, 1;
            MoveL Offs(pPick, 0, 0, 40), v100, z50, suckTool\WObj:=arucoWobj;
            
            pPick.rot := OrientZYX(anglez + positionArray{4}, angley, anglex);
!            MoveJ Offs(pPick, 0, 0, 40), v100, z50, suckTool\WObj:=arucoWobj;
            
            anglez := EulerZYX(\Z, pPick.rot);
            pTarget.rot := OrientZYX(anglez, angley, anglex);
            
            MoveJ Offs(pTarget, 0, 0, 40), v100, z50, suckTool\WObj:=assWobj;
            MoveL pTarget, v100, z50, suckTool\WObj:=assWobj;
!            WaitDI diOkButton, 1;
            WaitTime 1.5;
            SetDO doValet2, 0;
            WaitTime 1;
            MoveL Offs(pTarget, 0, 0, 40), v100, z50, suckTool\WObj:=assWobj;
            
            RobotClienSendMessage("PickNPlace done!");
        ELSE
            MoveJ pHome, v100, z50, suckTool\WObj:=wobj0;
            RobotClienSendMessage("PickNPlace done!");
        ENDIF 
	ENDPROC
ENDMODULE